{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Backlinks with context: build-time computation of which pages link to
-- each page, including the sentence that contains each link.
--
-- Architecture (dependency-correct, no circular deps):
--
--   1. Each content file is compiled under @version "links"@: a lightweight
--      pass that parses the source, walks the AST block-by-block, splits
--      each paragraph into sentences, and for every internal link records
--      the URL *and* the HTML of the sentence that contains it. The result
--      is serialised as a JSON array of @{url, context}@ objects.
--
--   2. A @create ["data/backlinks.json"]@ rule loads all "links" items,
--      inverts the map, and serialises
--      @target → [{url, title, abstract, context}]@ as JSON.
--
--   3. @backlinksField@ loads that JSON at page render time and injects
--      an HTML list showing each source's title and a quoted sentence of
--      context. The @load@ call establishes a proper Hakyll dependency so
--      pages recompile when backlinks change.
--
-- Dependency order (no cycles):
--   content "links" versions → data/backlinks.json → content default versions
module Backlinks
    ( backlinkRules
    , backlinksField
    , referencedByField
    ) where

import           Data.List                  (nubBy, partition, sortBy,
                                             stripPrefix)
import           Data.Ord                   (comparing)
import           Data.Maybe                 (fromMaybe)
import qualified Data.Map.Strict            as Map
import           Data.Map.Strict            (Map)
import qualified Data.ByteString            as BS
import qualified Data.Text                  as T
import qualified Data.Text.Lazy             as TL
import qualified Data.Text.Lazy.Encoding    as TLE
import qualified Data.Text.Encoding         as TE
import qualified Data.Text.Encoding.Error   as TE
import qualified Data.Aeson                 as Aeson
import           Data.Aeson                 ((.=))
import           Text.Pandoc.Class          (runPure)
import           Text.Pandoc.Writers        (writeHtml5String)
import           Text.Pandoc.Definition     (Block (..), Inline (..), Pandoc (..),
                                             nullMeta)
import           Text.Pandoc.Options        (WriterOptions (..), HTMLMathMethod (..))
import           Text.Pandoc.Walk           (query)
import           Hakyll
import           Compilers                  (readerOpts, writerOpts)
import           Filters                    (preprocessSource)
import qualified Patterns                   as P
import           ArchiveIndex               (archiveSlugFor)
import           Utils                      (canonicalUrlPath)

-- ---------------------------------------------------------------------------
-- Link-with-context entry (intermediate, saved by the "links" pass)
-- ---------------------------------------------------------------------------

data LinkEntry = LinkEntry
    { leUrl       :: T.Text   -- internal URL (as found in the AST)
    , leSentence  :: String   -- HTML of the sentence containing the link
    , leParagraph :: String   -- HTML of the full surrounding paragraph
    } deriving (Show, Eq)

instance Aeson.ToJSON LinkEntry where
    toJSON e = Aeson.object
        [ "url"       .= leUrl e
        , "sentence"  .= leSentence e
        , "paragraph" .= leParagraph e
        ]

instance Aeson.FromJSON LinkEntry where
    parseJSON = Aeson.withObject "LinkEntry" $ \o ->
        LinkEntry
            <$> o Aeson..: "url"
            <*> o Aeson..: "sentence"
            <*> o Aeson..: "paragraph"

-- ---------------------------------------------------------------------------
-- Backlink source record (stored in data/backlinks.json)
-- ---------------------------------------------------------------------------

data BacklinkSource = BacklinkSource
    { blUrl       :: String
    , blTitle     :: String
    , blAbstract  :: String
    , blSentence  :: String   -- raw HTML of the sentence containing the link
    , blParagraph :: String   -- raw HTML of the full paragraph (hover popup)
    , blFragment  :: String   -- archived-target fragment (no '#'), else ""
    } deriving (Show, Eq, Ord)

instance Aeson.ToJSON BacklinkSource where
    toJSON bl = Aeson.object
        [ "url"       .= blUrl bl
        , "title"     .= blTitle bl
        , "abstract"  .= blAbstract bl
        , "sentence"  .= blSentence bl
        , "paragraph" .= blParagraph bl
        , "fragment"  .= blFragment bl
        ]

instance Aeson.FromJSON BacklinkSource where
    parseJSON = Aeson.withObject "BacklinkSource" $ \o ->
        BacklinkSource
            <$> o Aeson..:  "url"
            <*> o Aeson..:  "title"
            <*> o Aeson..:  "abstract"
            <*> o Aeson..:  "sentence"
            <*> o Aeson..:  "paragraph"
            <*> o Aeson..:? "fragment" Aeson..!= ""

-- ---------------------------------------------------------------------------
-- Writer options for context rendering
-- ---------------------------------------------------------------------------

-- | Minimal writer options for rendering paragraph context: no template
-- (fragment only), plain math fallback (context excerpts are previews, not
-- full renders, and KaTeX CSS may not be loaded on all target pages).
contextWriterOpts :: WriterOptions
contextWriterOpts = writerOpts
    { writerTemplate       = Nothing
    , writerHTMLMathMethod = PlainMath
    }

-- ---------------------------------------------------------------------------
-- Context extraction
-- ---------------------------------------------------------------------------

-- | URL filter: skip external links, pseudo-schemes, anchor-only fragments,
-- and static-asset paths.
isPageLink :: T.Text -> Bool
isPageLink u
    -- An archived external URL is kept regardless of scheme or extension:
    -- pass 2 inverts it to its /archive/<slug>/ page.
    | isArchived = True
    | otherwise  =
        not (T.isPrefixOf "http://"  u) &&
        not (T.isPrefixOf "https://" u) &&
        -- protocol-relative //host/path is external, not a page path
        not (T.isPrefixOf "//"       u) &&
        not (T.isPrefixOf "#"        u) &&
        not (T.isPrefixOf "mailto:"  u) &&
        not (T.isPrefixOf "tel:"     u) &&
        not (T.null u) &&
        not (hasStaticExt u)
  where
    isArchived = case archiveSlugFor u of
                     Just _  -> True
                     Nothing -> False
    staticExts = [".pdf",".svg",".png",".jpg",".jpeg",".webp",
                  ".mp3",".mp4",".woff2",".woff",".ttf",".ico",
                  ".json",".asc",".xml",".gz",".zip"]
    hasStaticExt x = any (`T.isSuffixOf` T.toLower x) staticExts

-- | Render a list of inlines to an HTML fragment string.
-- Uses Plain (not Para) to avoid a wrapping <p> — callers add their own.
renderInlines :: [Inline] -> String
renderInlines inlines =
    case runPure (writeHtml5String contextWriterOpts doc) of
        Left  _   -> ""
        Right txt -> T.unpack txt
  where
    doc = Pandoc nullMeta [Plain inlines]

-- | Split a list of inlines into sentences by terminator punctuation.
--
-- A @Str@ whose last non-closing-punctuation character is @.@, @!@, or @?@
-- ends a sentence when followed by @Space@, @SoftBreak@, @LineBreak@, or
-- end-of-list. Closing quote/bracket characters after the terminator
-- (e.g. @right-double-quote@, @)@, @]@) are tolerated.
--
-- The splitter is deliberately simple: abbreviations like "e.g." or "Dr."
-- will cause occasional over-splitting. That is acceptable for backlink
-- previews, where a slightly short context is preferable to the complexity
-- of abbreviation detection.
splitSentences :: [Inline] -> [[Inline]]
splitSentences = go []
  where
    go acc [] = if null acc then [] else [reverse acc]
    go acc (tok : rest)
        | isTerminator tok && leadingBreak rest =
            reverse (tok : acc) : go [] (dropLeadingBreak rest)
        | otherwise =
            go (tok : acc) rest

    isTerminator :: Inline -> Bool
    isTerminator (Str s) = endsWithTerminator s
    isTerminator _       = False

    endsWithTerminator :: T.Text -> Bool
    endsWithTerminator t =
        case T.unsnoc (T.dropWhileEnd isClosingPunct t) of
            Just (_, c) -> c == '.' || c == '!' || c == '?'
            Nothing     -> False

    isClosingPunct :: Char -> Bool
    isClosingPunct c = c `elem` (")]\"'\x201D\x2019" :: String)

    leadingBreak :: [Inline] -> Bool
    leadingBreak []              = True
    leadingBreak (Space     : _) = True
    leadingBreak (SoftBreak : _) = True
    leadingBreak (LineBreak : _) = True
    leadingBreak _               = False

    dropLeadingBreak :: [Inline] -> [Inline]
    dropLeadingBreak (Space     : xs) = xs
    dropLeadingBreak (SoftBreak : xs) = xs
    dropLeadingBreak (LineBreak : xs) = xs
    dropLeadingBreak xs               = xs

-- | Extract @LinkEntry@ records from a Pandoc document.
-- For every internal link in a paragraph, emit an entry carrying the HTML
-- of the sentence containing the link (default display) and the HTML of
-- the full paragraph (hover/popup context).
-- Recurses into Div, BlockQuote, BulletList, OrderedList, and
-- DefinitionList. @Plain@ matters as much as @Para@: Pandoc renders
-- tight list items (the default @- item@ Markdown form) as @Plain@
-- blocks, so without it every link written in a tight list would be
-- invisible to the backlinks system.
extractLinksWithContext :: Pandoc -> [LinkEntry]
extractLinksWithContext (Pandoc _ blocks) = concatMap go blocks
  where
    go :: Block -> [LinkEntry]
    go (Para inlines)         = paraEntries inlines
    go (Plain inlines)        = paraEntries inlines
    go (BlockQuote bs)        = concatMap go bs
    go (Div _ bs)             = concatMap go bs
    go (BulletList items)     = concatMap (concatMap go) items
    go (OrderedList _ items)  = concatMap (concatMap go) items
    go (DefinitionList defs)  = concatMap defEntries defs
    go _                      = []

    defEntries :: ([Inline], [[Block]]) -> [LinkEntry]
    defEntries (term, bodies) =
        paraEntries term ++ concatMap (concatMap go) bodies

    paraEntries :: [Inline] -> [LinkEntry]
    paraEntries inlines =
        let paraHtml  = renderInlines inlines
            sentences = splitSentences inlines
        in  concatMap (sentenceEntries paraHtml) sentences

    sentenceEntries :: String -> [Inline] -> [LinkEntry]
    sentenceEntries paraHtml sentence =
        let urls = filter isPageLink (query getUrl sentence)
        in  if null urls then []
            else
                let sentHtml = renderInlines sentence
                in  map (\u -> LinkEntry u sentHtml paraHtml) urls

    getUrl :: Inline -> [T.Text]
    getUrl (Link _ _ (url, _)) = [url]
    getUrl _                   = []

-- ---------------------------------------------------------------------------
-- Lightweight links compiler
-- ---------------------------------------------------------------------------

-- | Compile a source file lightly: parse the Markdown (wikilinks preprocessed),
-- extract internal links with their paragraph context, and serialise as JSON.
linksCompiler :: Compiler (Item String)
linksCompiler = do
    body <- getResourceBody
    let src   = itemBody body
    let body' = itemSetBody (preprocessSource src) body
    pandocItem <- readPandocWith readerOpts body'
    let entries = nubBy sameEntry
                        (extractLinksWithContext (itemBody pandocItem))
    makeItem . TL.unpack . TLE.decodeUtf8 . Aeson.encode $ entries
  where
    sameEntry a b =
        leUrl       a == leUrl       b &&
        leSentence  a == leSentence  b &&
        leParagraph a == leParagraph b

-- ---------------------------------------------------------------------------
-- URL normalisation
-- ---------------------------------------------------------------------------

-- | Normalise an internal URL as a map key: strip query string and
-- fragment; ensure a leading slash; strip a trailing @index.html@
-- (keeping the directory slash) before the bare @.html@ extension, so a
-- page routed @essays\/foo\/index.html@ and a body link authored in the
-- canonical directory form @\/essays\/foo\/@ collide on the same key
-- (mirrors 'SimilarLinks.normaliseUrl'); percent-decode the path so that
-- @\/essays\/caf%C3%A9@ and @\/essays\/café@ collide on the same key.
--
-- Both sides of the backlink join go through this function: page keys
-- via 'backlinksFieldWith' (@normaliseUrl ("/" ++ route)@) and link
-- targets via 'targetKey' — so the two always agree.
normaliseUrl :: String -> String
normaliseUrl url =
    let t  = T.pack url
        t1 = fst (T.breakOn "?" (fst (T.breakOn "#" t)))
        t2 = if T.isPrefixOf "/" t1 then t1 else "/" `T.append` t1
        t3 = fromMaybe t2 (T.stripSuffix "index.html" t2)
        t4 = fromMaybe t3 (T.stripSuffix ".html" t3)
    in  percentDecode (T.unpack t4)

-- | Decode percent-escapes (@%XX@) into raw bytes, then re-interpret the
-- resulting bytestring as UTF-8. Invalid escapes are passed through
-- verbatim so this is safe to call on already-decoded input.
percentDecode :: String -> String
percentDecode = T.unpack . TE.decodeUtf8With lenientDecode . pack . go
  where
    go []                 = []
    go ('%':a:b:rest)
        | Just hi <- hexDigit a
        , Just lo <- hexDigit b
        = fromIntegral (hi * 16 + lo) : go rest
    go (c:rest)           = fromIntegral (fromEnum c) : go rest

    hexDigit c
        | c >= '0' && c <= '9' = Just (fromEnum c - fromEnum '0')
        | c >= 'a' && c <= 'f' = Just (fromEnum c - fromEnum 'a' + 10)
        | c >= 'A' && c <= 'F' = Just (fromEnum c - fromEnum 'A' + 10)
        | otherwise            = Nothing

    pack = BS.pack
    lenientDecode = TE.lenientDecode

-- ---------------------------------------------------------------------------
-- Archive-aware target keying
-- ---------------------------------------------------------------------------

-- | The @data/backlinks.json@ key an outbound URL inverts to. An archived
-- external URL canonicalises to its @/archive/<slug>/@ page key — computed
-- exactly as 'backlinksFieldWith' computes the archive page's own key (the
-- same string fed through 'normaliseUrl'), so the two always agree. Every
-- other URL is normalised as before.
targetKey :: T.Text -> T.Text
targetKey u = case archiveSlugFor u of
    Just slug -> T.pack (normaliseUrl ("/archive/" ++ slug ++ "/index.html"))
    Nothing   -> T.pack (normaliseUrl (T.unpack u))

-- | The fragment (without @#@) of an archived URL, for granular grouping
-- of "Referenced by". Empty for a non-archived URL or one with no fragment
-- — so granular grouping stays an archive-only behaviour.
archiveFragment :: T.Text -> String
archiveFragment u = case archiveSlugFor u of
    Just _  -> T.unpack (T.drop 1 (T.dropWhile (/= '#') u))
    Nothing -> ""

-- ---------------------------------------------------------------------------
-- Content patterns (must match the rules in Site.hs — sourced from
-- Patterns.allContent so additions to the canonical list automatically
-- propagate to backlinks).
-- ---------------------------------------------------------------------------

allContent :: Pattern
allContent = P.allContent

-- ---------------------------------------------------------------------------
-- Hakyll rules
-- ---------------------------------------------------------------------------

-- | Register the @version "links"@ rules for all content and the
-- @create ["data/backlinks.json"]@ rule.  Call this from 'Site.rules'.
backlinkRules :: Rules ()
backlinkRules = do
    -- Pass 1: extract links + context from each content file.
    match allContent $ version "links" $
        compile linksCompiler

    -- Pass 2: invert the map and write the backlinks JSON.
    create ["data/backlinks.json"] $ do
        route   idRoute
        compile $ do
            items <- loadAll (allContent .&&. hasVersion "links")
                        :: Compiler [Item String]
            pairs <- concat <$> mapM toSourcePairs items
            makeItem . TL.unpack . TLE.decodeUtf8 . Aeson.encode
                $ Map.fromListWith (++) [(k, [v]) | (k, v) <- pairs]

-- | For one "links" item, produce @(normalised-target-url, BacklinkSource)@
-- pairs — one per internal link found in the source file.
toSourcePairs :: Item String -> Compiler [(T.Text, BacklinkSource)]
toSourcePairs item = do
    let ident0   = setVersion Nothing (itemIdentifier item)
    mRoute       <- getRoute ident0
    meta         <- getMetadata ident0
    -- The href a reader clicks, so it is the canonical directory form —
    -- not the raw route, which for a directory-routed essay ends in
    -- index.html and would be the site's only surviving link to the
    -- second spelling of a page (audit C03). This is the display URL
    -- only; the join key is 'normaliseUrl', which strips both spellings.
    let srcUrl   = maybe "" canonicalUrlPath mRoute
    let title    = fromMaybe "(untitled)" (lookupString "title" meta)
    let abstract = fromMaybe "" (lookupString "abstract" meta)
    case mRoute of
        Nothing -> return []
        Just _  ->
            case Aeson.decodeStrict (TE.encodeUtf8 (T.pack (itemBody item)))
                    :: Maybe [LinkEntry] of
                Nothing      -> return []
                Just entries ->
                    return [ ( targetKey (leUrl e)
                             , BacklinkSource srcUrl title abstract
                                              (leSentence  e)
                                              (leParagraph e)
                                              (archiveFragment (leUrl e))
                             )
                           | e <- entries ]

-- ---------------------------------------------------------------------------
-- Context field
-- ---------------------------------------------------------------------------

-- | Context field @$backlinks$@ that injects an HTML list of pages that link
-- to the current page, each with its paragraph context.
-- Returns @noResult@ (so @$if(backlinks)$@ is false) when there are none.
backlinksField :: Context String
backlinksField = backlinksFieldWith renderBacklinks "backlinks"

-- | "Referenced by" for archive pages. Same lookup as 'backlinksField',
-- but the sources are grouped by the fragment each citation targets, so an
-- archived work's page can show which section/page each citing essay points
-- at (granular backlinks).
referencedByField :: Context String
referencedByField = backlinksFieldWith renderReferencedBy "referenced-by"

-- | Shared machinery for 'backlinksField' and 'referencedByField': look the
-- page up in @data/backlinks.json@ by its normalised route, then hand the
-- sorted sources to the given renderer.
backlinksFieldWith :: ([BacklinkSource] -> String) -> String -> Context String
backlinksFieldWith renderSources name = field name $ \item -> do
    blItem <- load (fromFilePath "data/backlinks.json") :: Compiler (Item String)
    case Aeson.decodeStrict (TE.encodeUtf8 (T.pack (itemBody blItem)))
            :: Maybe (Map T.Text [BacklinkSource]) of
        Nothing    -> noResult "backlinks: could not parse data/backlinks.json"
        Just blMap -> do
            mRoute <- getRoute (itemIdentifier item)
            case mRoute of
                Nothing -> fail "backlinks: item has no route"
                Just r  ->
                    let key     = T.pack (normaliseUrl ("/" ++ r))
                        sources = fromMaybe [] (Map.lookup key blMap)
                        sorted  = sortBy (comparing blTitle) sources
                    in  if null sorted
                        then fail "no backlinks"
                        else return (renderSources sorted)

-- ---------------------------------------------------------------------------
-- HTML rendering
-- ---------------------------------------------------------------------------

-- | Render backlink sources as an HTML list. Each item shows:
--   * the source title as a link (serif body face),
--   * a <blockquote> of the sentence containing the link (default context),
--   * a small hoverable "¶" affordance that reveals the full paragraph in
--     a CSS-driven popup when hovered or keyboard-focused.
--
-- 'blSentence' and 'blParagraph' are already HTML fragments produced by
-- the Pandoc writer, so they are emitted unescaped.
renderBacklinks :: [BacklinkSource] -> String
renderBacklinks sources =
    "<ul class=\"backlinks-list\">\n"
    ++ concatMap renderBacklinkItem sources
    ++ "</ul>"

-- | "Referenced by", grouped by the fragment each citation targets.
-- Sources citing the work with no fragment render first as a plain list;
-- each distinct fragment then gets its own subheading. With no fragments
-- anywhere (the common case) this collapses to exactly the flat list.
renderReferencedBy :: [BacklinkSource] -> String
renderReferencedBy sources =
    let (general, fragmented) = partition (null . blFragment) sources
        groups = Map.toList $ Map.fromListWith (flip (++))
                     [ (blFragment s, [s]) | s <- fragmented ]
    in  renderList general ++ concatMap renderGroup groups
  where
    renderList [] = ""
    renderList ss = "<ul class=\"backlinks-list\">\n"
                    ++ concatMap renderBacklinkItem ss ++ "</ul>\n"
    renderGroup (frag, ss) =
        "<div class=\"referenced-by-group\">"
        ++ "<h3 class=\"referenced-by-fragment\">"
        ++ escapeHtml (fragmentLabel frag) ++ "</h3>"
        ++ renderList ss
        ++ "</div>\n"

-- | Human label for a cited fragment: a PDF @#page=N@ becomes "Page N";
-- any other @#anchor@ is shown verbatim behind a section mark.
fragmentLabel :: String -> String
fragmentLabel frag =
    case stripPrefix "page=" frag of
        Just n  -> "Page " ++ n
        Nothing -> "\x00A7 " ++ frag

-- | One backlink @<li>@: the source title as a link, the sentence of
-- context as a blockquote, and a hover affordance revealing the full
-- paragraph. 'blSentence' / 'blParagraph' are already HTML fragments from
-- the Pandoc writer, so they are emitted unescaped.
renderBacklinkItem :: BacklinkSource -> String
renderBacklinkItem bl =
    "<li class=\"backlink-item\">"
    ++ "<a class=\"backlink-source\" href=\""
    ++ escapeHtml (blUrl bl) ++ "\">"
    ++ escapeHtml (blTitle bl) ++ "</a>"
    ++ ( if null (blSentence bl) then ""
         else "<blockquote class=\"backlink-quote\">"
              ++ blSentence bl
              ++ paragraphAffordance
              ++ "</blockquote>" )
    ++ "</li>\n"
  where
    paragraphAffordance
        | null (blParagraph bl)            = ""
        | blParagraph bl == blSentence bl  = ""
        | otherwise                        =
            "<span class=\"backlink-full\">"
            ++ "<button type=\"button\" class=\"backlink-full-trigger\""
            ++ " aria-label=\"Show full paragraph\" tabindex=\"0\">\x00B6</button>"
            ++ "<span class=\"backlink-full-popup\" role=\"tooltip\">"
            ++ blParagraph bl
            ++ "</span>"
            ++ "</span>"

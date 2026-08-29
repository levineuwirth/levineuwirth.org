{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
module Contexts
    ( siteCtx
    , essayCtx
    , postCtx
    , pageCtx
    , poetryCtx
    , fictionCtx
    , compositionCtx
    , declaresScore
    , scorePageList
    , photographyCtx
    , contentKindField
    , abstractField
    , descriptionField
    , tagLinksField
    , tagLinksFieldExcludingScope
    , tagLinksFieldExcludingTopSegment
    , keywordLinksField
    , authorLinksField
    , dateDisplayField
    , revisionDateFields
    , recentFirstByDisplay
    , Revision (..)
    , getRevisions
    , isProvedConfidence
    ) where

import Control.Exception       (IOException, try)
import Data.Aeson              (Value (..))
import qualified Data.Aeson         as Aeson
import qualified Data.Aeson.Key     as AK
import qualified Data.Aeson.KeyMap  as KM
import qualified Data.Vector        as V
import Data.Char               (isDigit, toLower)
import Data.List               (intercalate, isPrefixOf, sortBy)
import Data.Maybe              (fromMaybe, mapMaybe)
import Data.Ord                (comparing)
import qualified Data.Scientific    as Sci
import Data.Time.Calendar      (toGregorian)
import Data.Time.Clock         (UTCTime, getCurrentTime, utctDay)
import Data.Time.Format        (formatTime, defaultTimeLocale, parseTimeM)
import System.Directory        (doesFileExist)
import System.FilePath         (makeRelative, takeDirectory, takeFileName, (</>))
import System.IO               (hPutStrLn, stderr)
import Text.Read               (readMaybe)
import qualified Data.Text     as T
import qualified Data.Text.IO  as TIO
import qualified Data.Yaml     as Y
import Text.Pandoc             (runPure, readMarkdown, writeHtml5String, writePlain, Pandoc(..), Block(..), Inline(..))
import Text.Pandoc.Options     (WriterOptions(..), HTMLMathMethod(..))
import Hakyll       hiding (trim)
import Backlinks    (backlinksField)
import Dingbat      (dingbatField)
import Marks        (monogramSvgField, hasMonogramField, epistemicSvgField)
import SimilarLinks (similarLinksField)
import Stability    (stabilityField, lastReviewedField, lastReviewedIsoField,
                     versionHistoryField,
                     versionHistoryPrimaryField, versionHistoryRestField,
                     versionHistoryRangeField, versionHistoryRangeStartField,
                     versionHistoryRangeEndField, versionHistoryCommitsField)
import Utils        (authorSlugify, authorNameOf, trim)

-- | Returns 'True' when the @confidence:@ frontmatter value is the
--   "proved" / "proven" sentinel — the §4.3 carve-out for formal proofs
--   that opt out of a numeric credence. Case-insensitive.
isProvedConfidence :: Maybe String -> Bool
isProvedConfidence (Just s) = map toLower (trim s) `elem` ["proved", "proven"]
isProvedConfidence _        = False

-- ---------------------------------------------------------------------------
-- Affiliation field
-- ---------------------------------------------------------------------------

-- | Parses the @affiliation@ frontmatter key and exposes each entry as
--   @affiliation-name@ / @affiliation-url@ pairs.
--
--   Accepts a scalar string or a YAML list. Each entry may use pipe syntax:
--     @"Brown University | https://cs.brown.edu"@
--   Entries without a URL still produce a row; @affiliation-url@ fails
--   (evaluates to noResult), so @$if(affiliation-url)$@ works in templates.
--
--   Usage:
--     $for(affiliation-links)$
--       $if(affiliation-url)$<a href="$affiliation-url$">$affiliation-name$</a>
--       $else$$affiliation-name$$endif$$sep$ · $endfor$
affiliationField :: Context a
affiliationField = listFieldWith "affiliation-links" ctx $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    let entries = case lookupStringList "affiliation" meta of
                    Just xs -> xs
                    Nothing -> maybe [] (:[]) (lookupString "affiliation" meta)
    -- noResult, not an empty list: Hakyll's $if$ treats an empty
    -- ListField as truthy, so returning [] would render the wrapper
    -- markup (an empty .meta-affiliation row) on every page.
    if null entries
        then noResult "no affiliation"
        else return $ map (Item (fromFilePath "") . parseEntry) entries
  where
    ctx = field "affiliation-name" (return . fst . itemBody)
       <> field "affiliation-url"  (\i -> let u = snd (itemBody i)
                                           in if null u then noResult "no url" else return u)
    parseEntry s = case break (== '|') s of
        (name, '|' : url) -> (trim name, trim url)
        (name, _)         -> (trim name, "")

-- ---------------------------------------------------------------------------
-- Build time field
-- ---------------------------------------------------------------------------

-- | Resolves to the time the current item was compiled, formatted as
--   "Saturday, November 15th, 2025 15:05:55" (UTC).
buildTimeField :: Context String
buildTimeField = field "build-time" $ \_ ->
    unsafeCompiler $ do
        t <- getCurrentTime
        let (_, _, d) = toGregorian (utctDay t)
            prefix    = formatTime defaultTimeLocale "%A, %B " t
            suffix    = formatTime defaultTimeLocale ", %Y %H:%M:%S" t
        return (prefix ++ show d ++ ordSuffix d ++ suffix)
  where
    ordSuffix n
        | n `elem` [11,12,13] = "th"
        | n `mod` 10 == 1     = "st"
        | n `mod` 10 == 2     = "nd"
        | n `mod` 10 == 3     = "rd"
        | otherwise            = "th"

-- ---------------------------------------------------------------------------
-- Content kind field
-- ---------------------------------------------------------------------------

-- | @$item-kind$@: human-readable content type derived from the item's route.
-- Used on the New page to label each entry (Essay, Post, Poem, etc.).
contentKindField :: Context String
contentKindField = field "item-kind" $ \item -> do
    r <- getRoute (itemIdentifier item)
    return $ case r of
        Nothing -> "Page"
        Just r'
            | "essays/"      `isPrefixOf` r' -> "Essay"
            | "blog/"        `isPrefixOf` r' -> "Post"
            | "poetry/"      `isPrefixOf` r' -> "Poem"
            | "fiction/"     `isPrefixOf` r' -> "Fiction"
            | "music/"       `isPrefixOf` r' -> "Composition"
            | "photography/" `isPrefixOf` r' -> "Photo"
            | otherwise                       -> "Page"

-- ---------------------------------------------------------------------------
-- Site-wide context
-- ---------------------------------------------------------------------------

-- | @$page-scripts$@ — list field providing @$script-src$@ for each entry
-- in the @js:@ frontmatter key (accepts a scalar string or a YAML list).
-- Returns an empty list when absent; $for iterates zero times, emitting nothing.
-- NOTE: do not use fail here — $for does not catch noResult the way $if does.
--
-- Each child Item is keyed on @<parent-identifier>#js-<index>@ so that two
-- pages referencing the same script path (e.g. @shared.js@) do not collide
-- in Hakyll's item store.
pageScriptsField :: Context String
pageScriptsField = listFieldWith "page-scripts" ctx $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    let scripts = case lookupStringList "js" meta of
                    Just xs -> xs
                    Nothing -> maybe [] (:[]) (lookupString "js" meta)
        parent  = toFilePath (itemIdentifier item)
    return $ zipWith
        (\i s -> Item (fromFilePath (parent ++ "#js-" ++ show (i :: Int))) s)
        [0 ..]
        scripts
  where
    ctx = field "script-src" (return . itemBody)

-- ---------------------------------------------------------------------------
-- Tag links field
-- ---------------------------------------------------------------------------

-- | List context field exposing an item's own (non-expanded) tags as
--   @tag-name@ / @tag-url@ objects.
--
--   Fails with 'noResult' when the item has no tags — same discipline
--   as the @Excluding@ variants below — so @$if(...)$@ gates are false
--   and templates don't emit empty tag-wrapper markup.
--
--   $for(essay-tags)$<a href="$tag-url$">$tag-name$</a>$endfor$
tagLinksField :: String -> Context a
tagLinksField fieldName = listFieldWith fieldName ctx $ \item -> do
    ts <- getTags (itemIdentifier item)
    if null ts
        then noResult "no tags"
        else return (map toItem ts)
  where
    toItem t = Item (fromFilePath (t ++ "/index.html")) t
    ctx      = field "tag-name" (return . itemBody)
            <> field "tag-url"  (\i -> return $ "/" ++ itemBody i ++ "/")

-- | Variant of 'tagLinksField' that suppresses tags equal to or ancestral
--   to the given scope. Used on tag index pages to hide the redundant
--   filing ribbon entry for the current page's own scope.
--
--   Suppression is equality-based on the scope plus its prefix-ancestors:
--   on @\/nonfiction\/@ (scope = @"nonfiction"@) only the literal
--   @"nonfiction"@ tag is hidden; @"nonfiction/philosophy"@ still renders.
--   On @\/nonfiction\/philosophy\/@ both @"nonfiction"@ and
--   @"nonfiction/philosophy"@ are hidden; sibling and cross-filed tags
--   remain.
--
--   When every tag is suppressed, the field fails with 'noResult' so
--   @$if(...)$@ is false and the tag-ribbon wrapper is omitted entirely
--   instead of rendering as an empty @<div>@.
tagLinksFieldExcludingScope :: String -> String -> Context a
tagLinksFieldExcludingScope fieldName scope =
    listFieldWith fieldName ctx $ \item -> do
        ts <- getTags (itemIdentifier item)
        let visible = filter (not . isScopeOrAncestor) ts
        if null visible
            then noResult "no visible tags after scope suppression"
            else return (map toItem visible)
  where
    toItem t = Item (fromFilePath (t ++ "/index.html")) t
    ctx      = field "tag-name" (return . itemBody)
            <> field "tag-url"  (\i -> return $ "/" ++ itemBody i ++ "/")
    -- Hide tag t when t == scope, or when t is a strict prefix-ancestor
    -- of scope (i.e., scope starts with t ++ "/"). Descendants of scope
    -- (e.g., "nonfiction/philosophy" when scope="nonfiction") are kept.
    isScopeOrAncestor t = t == scope || (t ++ "/") `isPrefixOf` scope

-- | Variant of 'tagLinksField' that suppresses any tag whose top
--   (slash-separated) segment equals the given scope. Used by the
--   Library page: an item rendered under the "Research" section
--   should not re-list its own @research\/*@ filings in the tag
--   footer (the section heading makes those structurally implied),
--   but should still list @tech\/*@ cross-filings.
--
--   This is distinct from 'tagLinksFieldExcludingScope', which
--   suppresses only exact-match and strict ancestors. Library's
--   redundancy goal is broader: hide the whole subtree rooted at
--   the section's portal, not just the portal tag itself.
--
--   @
--   scope = "research"
--     t = "research"              → hide  (top = "research" == scope)
--     t = "research/cryptography" → hide  (top = "research" == scope)
--     t = "tech"                  → show  (top = "tech"     /= scope)
--     t = "tech/hpc"              → show  (top = "tech"     /= scope)
--   @
--
--   'noResult' fires when every tag is suppressed so
--   @$if(item-tags)$@ gates off an empty footer wrapper, same
--   discipline as 'tagLinksFieldExcludingScope'.
tagLinksFieldExcludingTopSegment :: String -> String -> Context a
tagLinksFieldExcludingTopSegment fieldName scope =
    listFieldWith fieldName ctx $ \item -> do
        ts <- getTags (itemIdentifier item)
        let visible = filter (not . matchesTopSegment) ts
        if null visible
            then noResult "no cross-portal tags after top-segment suppression"
            else return (map toItem visible)
  where
    toItem t = Item (fromFilePath (t ++ "/index.html")) t
    ctx      = field "tag-name" (return . itemBody)
            <> field "tag-url"  (\i -> return $ "/" ++ itemBody i ++ "/")
    matchesTopSegment t = takeWhile (/= '/') t == scope

-- ---------------------------------------------------------------------------
-- Keyword links field (bibliography-scoped vocabulary, Phase 6a)
-- ---------------------------------------------------------------------------

-- | List context field exposing an item's @keywords:@ frontmatter as
--   @$kw-name$@ / @$kw-url$@ pairs. URL targets @/bibliography/\<kw\>/@,
--   the per-keyword bibliography pages (built by Phase 6b; links will
--   404 until then, deliberately — the mechanism has to be in place
--   before the pages can be populated).
--
--   Shared vocabulary with bib-entry @keywords:@ fields parsed by
--   'BibExtras.parseBibExtras'. An essay tagged with the same keyword
--   as a bib entry will appear alongside that entry on the keyword
--   page.
--
--   Accepts both YAML list and comma-separated scalar forms:
--
--   @
--   keywords: [crypto, lattices]
--   keywords:
--     - crypto
--     - lattices
--   keywords: "crypto, lattices"
--   @
--
--   Returns @noResult@ when absent or empty so the template's
--   @$if(essay-keywords)$@ gate suppresses the meta row.
--
--   Usage in metadata.html:
--
--   @
--   $for(essay-keywords)$\<a class="meta-keyword" href="$kw-url$"\>$kw-name$\</a\>$endfor$
--   @
keywordLinksField :: String -> Context a
keywordLinksField fieldName = listFieldWith fieldName ctx $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    let kws = case lookupStringList "keywords" meta of
            Just xs -> xs
            Nothing -> case lookupString "keywords" meta of
                Just s  -> filter (not . null) (map trim (splitOn ',' s))
                Nothing -> []
        visible = filter (not . null . trim) kws
    if null visible
        then noResult "no keywords"
        else return (map toItem visible)
  where
    toItem k = Item (fromFilePath (k ++ "/index.html")) k
    ctx = field "kw-name" (return . itemBody)
       <> field "kw-url"  (\i -> return $ "/bibliography/" ++ itemBody i ++ "/")

    splitOn :: Char -> String -> [String]
    splitOn c s = case break (== c) s of
        (before, [])      -> [before]
        (before, _ : rest) -> before : splitOn c rest

-- ---------------------------------------------------------------------------
-- Author links field
-- ---------------------------------------------------------------------------
--
-- 'authorSlugify' and 'authorNameOf' are imported from 'Utils' so that
-- they cannot drift from the copies in 'Authors'.

-- | Exposes each item's authors as @author-name@ / @author-url@ pairs.
--   Defaults to Levi Neuwirth when no "authors" frontmatter key is present.
--
--   Entries that produce an empty name (e.g. @"| https://url"@) or an empty
--   slug (e.g. all-punctuation names) are dropped, so the field never emits
--   a @/authors//@ link.
--
--   $for(author-links)$<a href="$author-url$">$author-name$</a>$sep$, $endfor$
authorLinksField :: Context a
authorLinksField = listFieldWith "author-links" ctx $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    let entries = fromMaybe [] (lookupStringList "authors" meta)
        rawNames = if null entries then ["Levi Neuwirth"] else map authorNameOf entries
        validNames = filter (\n -> not (null n) && not (null (authorSlugify n))) rawNames
        names = if null validNames then ["Levi Neuwirth"] else validNames
    return $ map (\n -> Item (fromFilePath "") (n, "/authors/" ++ authorSlugify n ++ "/")) names
  where
    ctx = field "author-name" (return . fst . itemBody)
       <> field "author-url"  (return . snd . itemBody)

-- ---------------------------------------------------------------------------
-- Abstract field
-- ---------------------------------------------------------------------------

-- | Renders the abstract using Pandoc to support Markdown and LaTeX math.
--   Strips the outer @<p>@ wrapping. A single-paragraph abstract becomes a
--   bare @Plain@ so the rendered HTML is unwrapped inlines. A multi-paragraph
--   abstract (author used a blank line in the YAML literal block) is flattened
--   to a single @Plain@ with @LineBreak@ separators between what were
--   originally paragraph boundaries — the visual break is preserved without
--   emitting stray @<p>@ tags inside the metadata block. Mixed block content
--   (e.g. an abstract containing a blockquote) falls through unchanged.
abstractField :: Context String
abstractField = field "abstract" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString "abstract" meta of
        Nothing -> noResult "no abstract"
        Just src -> do
            let pandocResult = runPure $ do
                    doc <- readMarkdown defaultHakyllReaderOptions (T.pack src)
                    let doc' = case doc of
                                 Pandoc m [Para ils] -> Pandoc m [Plain ils]
                                 Pandoc m blocks
                                   | all isPara blocks && not (null blocks) ->
                                       let joined = intercalate [LineBreak]
                                                      [ils | Para ils <- blocks]
                                       in Pandoc m [Plain joined]
                                 _ -> doc
                    let wOpts = defaultHakyllWriterOptions { writerHTMLMathMethod = MathML }
                    writeHtml5String wOpts doc'
            case pandocResult of
                Left err -> fail $ "Pandoc error rendering abstract: " ++ show err
                Right html -> return (T.unpack html)
  where
    isPara (Para _) = True
    isPara _        = False

-- ---------------------------------------------------------------------------
-- Description field
-- ---------------------------------------------------------------------------

-- | Renders the @abstract@ frontmatter key as plain text suitable for use in
--   @<meta name="description">@, @og:description@, and @twitter:description@.
--   Strips Pandoc markup, collapses internal whitespace, truncates to ~200
--   chars, and HTML-escapes attribute-special characters. Returns @noResult@
--   when no @abstract@ is present (so @$if(description)$@ short-circuits).
descriptionField :: Context String
descriptionField = field "description" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString "abstract" meta of
        Nothing  -> noResult "no abstract"
        Just src -> do
            let pandocResult = runPure $ do
                    doc <- readMarkdown defaultHakyllReaderOptions (T.pack src)
                    writePlain defaultHakyllWriterOptions doc
            case pandocResult of
                Left err  -> fail $ "Pandoc error rendering description: " ++ show err
                Right txt ->
                    let collapsed = T.unwords (T.words txt)
                        capped    = if T.length collapsed > 200
                                       then T.take 197 collapsed <> T.pack "\x2026"
                                       else collapsed
                    in  return (attrEscape (T.unpack capped))

-- | HTML-escape characters that would break out of an attribute value.
attrEscape :: String -> String
attrEscape = concatMap esc
  where
    esc '&'  = "&amp;"
    esc '<'  = "&lt;"
    esc '>'  = "&gt;"
    esc '"'  = "&quot;"
    esc '\'' = "&#39;"
    esc c    = [c]

-- ---------------------------------------------------------------------------
-- Summary field
-- ---------------------------------------------------------------------------

-- | Renders the @summary@ frontmatter key through Pandoc, preserving full
--   block structure (paragraphs, bold, lists). Unlike 'abstractField', no
--   paragraph flattening is applied because the summary renders inside its
--   own styled box rather than inline in the metadata strip.
summaryField :: Context String
summaryField = field "summary" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString "summary" meta of
        Nothing -> noResult "no summary"
        Just src -> do
            let pandocResult = runPure $ do
                    doc <- readMarkdown defaultHakyllReaderOptions (T.pack src)
                    let wOpts = defaultHakyllWriterOptions { writerHTMLMathMethod = MathML }
                    writeHtml5String wOpts doc
            case pandocResult of
                Left err -> fail $ "Pandoc error rendering summary: " ++ show err
                Right html -> return (T.unpack html)

siteCtx :: Context String
siteCtx =
    constField "site-title" "Levi Neuwirth"
    <> constField "site-url" "https://levineuwirth.org"
    <> buildTimeField
    <> pageScriptsField
    <> abstractField
    <> descriptionField
    <> summaryField
    <> dingbatField
    <> monogramSvgField
    <> hasMonogramField
    <> defaultContext

-- ---------------------------------------------------------------------------
-- Helper: load a named snapshot as a context field
-- ---------------------------------------------------------------------------

-- | @snapshotField name snap@ creates a context field @name@ whose value is
--   the body of the snapshot @snap@ saved for the current item.
snapshotField :: String -> Snapshot -> Context String
snapshotField name snap = field name $ \item ->
    itemBody <$> loadSnapshot (itemIdentifier item) snap

-- ---------------------------------------------------------------------------
-- Essay context
-- ---------------------------------------------------------------------------

-- | Bibliography field: loads the citation HTML saved by essayCompiler.
--   Returns noResult (making $if(bibliography)$ false) when empty.
--   Also provides $has-citations$ for conditional JS loading.
bibliographyField :: Context String
bibliographyField = bibContent <> hasCitations
  where
    bibContent = field "bibliography" $ \item -> do
        bib <- itemBody <$> loadSnapshot (itemIdentifier item) "bibliography"
        if null bib then noResult "no bibliography" else return bib
    hasCitations = field "has-citations" $ \item -> do
        bib <- itemBody <$> (loadSnapshot (itemIdentifier item) "bibliography"
                              :: Compiler (Item String))
        if null bib then noResult "no citations" else return "true"

-- | Further-reading field: loads the further-reading HTML saved by essayCompiler.
--   Returns noResult (making $if(further-reading-refs)$ false) when empty.
furtherReadingField :: Context String
furtherReadingField = field "further-reading-refs" $ \item -> do
    fr <- itemBody <$> (loadSnapshot (itemIdentifier item) "further-reading-refs"
                          :: Compiler (Item String))
    if null fr then noResult "no further reading" else return fr

-- ---------------------------------------------------------------------------
-- Epistemic fields
-- ---------------------------------------------------------------------------

-- | Render an integer 1–5 frontmatter key as filled/empty dot chars.
-- Returns @noResult@ when the key is absent, unparseable, or below 1
-- (a zero would otherwise render five empty circles); values above 5
-- clamp to 5.
dotsField :: String -> String -> Context String
dotsField ctxKey metaKey = field ctxKey $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString metaKey meta >>= readMaybe of
        Nothing -> noResult (ctxKey ++ ": not set")
        Just (n :: Int)
            | n < 1 -> noResult (ctxKey ++ ": value below the 1-5 scale")
            | otherwise ->
                let v = min 5 n
                in  return (replicate v '\x25CF' ++ replicate (5 - v) '\x25CB')

-- | @$confidence-trend$@: ↑, ↓, or → derived from the last two entries
-- in the @confidence-history@ frontmatter list.  Returns @noResult@ when
-- there is no history or only a single entry.
--
-- The arrow flips when the absolute change crosses 'trendThreshold'
-- (currently 5 percentage points). Smaller swings count as flat.
--
-- When @confidence: proved@ (or @proven@) is in effect, the arrow is
-- suppressed: a proof either holds or it does not, so tracking trend on
-- a binary-after-the-fact value is incoherent (MARKS.md §4.3). If the
-- frontmatter sets both @confidence: proved@ and @confidence-history:@
-- the build emits a warning and the history is ignored.
confidenceTrendField :: Context String
confidenceTrendField = field "confidence-trend" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    if isProvedConfidence (lookupString "confidence" meta)
        then do
            case lookupStringList "confidence-history" meta of
                Just _ -> unsafeCompiler $ hPutStrLn stderr $
                    "[Marks] " ++ toFilePath (itemIdentifier item) ++
                    ": confidence: proved is incompatible with confidence-history; ignoring history"
                Nothing -> return ()
            noResult "confidence is proved; trend suppressed"
        else case lookupStringList "confidence-history" meta of
            Nothing -> noResult "no confidence history"
            Just xs -> case lastTwo xs of
                Nothing            -> noResult "no confidence history"
                Just (prevS, curS) ->
                    let prev = readMaybe prevS :: Maybe Int
                        cur  = readMaybe curS  :: Maybe Int
                    in  case (prev, cur) of
                            (Just p, Just c)
                                | c - p >  trendThreshold -> return "\x2191"   -- ↑
                                | p - c >  trendThreshold -> return "\x2193"   -- ↓
                                | otherwise               -> return "\x2192"   -- →
                            _ -> return "\x2192"
  where
    trendThreshold :: Int
    trendThreshold = 5

    -- Total replacement for @(xs !! (length xs - 2), last xs)@: returns
    -- the last two elements of a list, in order, or 'Nothing' when the
    -- list has fewer than two entries.
    lastTwo :: [a] -> Maybe (a, a)
    lastTwo []        = Nothing
    lastTwo [_]       = Nothing
    lastTwo [a, b]    = Just (a, b)
    lastTwo (_ : rest) = lastTwo rest

-- | @$overall-score$@: weighted composite of confidence (60 %) and
--   evidence quality (40 %), expressed as an integer on a 0–100 scale.
--
--   Importance is intentionally excluded from the score: it answers
--   "should you read this?", not "should you trust it?", and folding
--   the two together inflated the number and muddied its meaning.
--   It still appears in the footer as an independent orientation
--   signal — just not as a credibility input.
--
--   The 1–5 evidence scale is rescaled as @(ev − 1) / 4@ rather than
--   plain @ev / 5@. The naive form left a hidden +6 floor (since
--   @1/5 = 0.2@) and a midpoint of 0.6 instead of 0.5; the rescale
--   makes evidence=1 contribute zero and evidence=3 contribute exactly
--   half, so a "true midpoint" entry (conf=50, ev=3) lands on 50.
--
--   Returns @noResult@ when confidence or evidence is absent, so
--   @$if(overall-score)$@ guards the template safely.
--
--   Formula:  raw   = conf/100 · 0.6 + (ev − 1)/4 · 0.4   (0–1)
--             score = clamp₀₋₁₀₀(round(raw · 100))
--
--   The @confidence: proved@ (or @proven@) sentinel — see MARKS.md §4.3 —
--   substitutes @conf = 100@ in the formula. Evidence still varies, so
--   trust is not pinned to 100; a complete proof with weak supporting
--   apparatus (evidence=1) lands at 60, the same as a numeric
--   confidence=100, evidence=1 entry would.
overallScoreField :: Context String
overallScoreField = field "overall-score" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    let readInt s = readMaybe s :: Maybe Int
        confRaw   = lookupString "confidence" meta
        confInt   = if isProvedConfidence confRaw
                       then Just 100
                       else readInt =<< confRaw
    case ( confInt
         , readInt =<< lookupString "evidence"   meta
         ) of
        (Just conf, Just ev) ->
            let raw :: Double
                raw   = fromIntegral conf       / 100.0 * 0.6
                      + fromIntegral (ev - 1)   / 4.0   * 0.4
                score = max 0 (min 100 (round (raw * 100.0) :: Int))
            in  return (show score)
        _ -> noResult "overall-score: confidence or evidence not set"

-- | @$confidence$@: numeric override that suppresses the @proved@ /
--   @proven@ sentinel. When the frontmatter value is parseable as an
--   integer this returns its 'show' form; otherwise 'noResult' so the
--   template's @$if(confidence)$@ guard collapses cleanly. The sentinel
--   case is surfaced via 'confidenceProvedField' instead.
--
--   Composed before 'defaultContext' so this override wins; without it
--   @$confidence$@ would render the literal string @"proved"@ and the
--   template's @$confidence$% confidence@ would print @"proved%
--   confidence"@.
confidenceField :: Context String
confidenceField = field "confidence" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString "confidence" meta of
        Nothing -> noResult "no confidence"
        Just s  -> case readMaybe (trim s) :: Maybe Int of
            Just n  -> return (show n)
            Nothing -> noResult "confidence not numeric"

-- | @$confidence-proved$@: present (renders as @"true"@) when
--   @confidence:@ is the @proved@ / @proven@ sentinel; 'noResult'
--   otherwise. Templates branch on this to render @"proved confidence"@
--   in place of the @"XX% confidence"@ chip.
confidenceProvedField :: Context String
confidenceProvedField = field "confidence-proved" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    if isProvedConfidence (lookupString "confidence" meta)
        then return "true"
        else noResult "confidence is not proved"

-- | @$peer-status$@: validated raw value (slug form) from the
--   @peer-status:@ frontmatter. Used by the template as a class-attribute
--   modifier (@ep-peer-status--retracted@ etc.). Invalid values warn and
--   degrade to 'noResult', so a typo doesn't render an unstyled chip.
--   Absent and @unreviewed@ both produce 'noResult' — the chip is the
--   exception, not the default.
peerStatusField :: Context String
peerStatusField = field "peer-status" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString "peer-status" meta of
        Nothing -> noResult "no peer-status"
        Just raw ->
            let s = map toLower (trim raw)
            in  if s `elem` knownPeerStatuses
                    then if s == "unreviewed"
                             then noResult "peer-status is unreviewed (default)"
                             else return s
                    else do
                        unsafeCompiler $ hPutStrLn stderr $
                            "[Marks] " ++ toFilePath (itemIdentifier item) ++
                            ": invalid peer-status value \"" ++ raw ++
                            "\"; treating as unreviewed"
                        noResult "invalid peer-status"
  where
    knownPeerStatuses = ["unreviewed", "under-review", "peer-reviewed",
                         "published", "retracted"]

-- | @$peer-status-display$@: human-readable form of the @peer-status@
--   value, suitable for the compact-row chip text. Per MARKS.md §4.1 the
--   display strings are:
--
--     * @under-review@   → @"under review"@   (hyphen → space)
--     * @peer-reviewed@  → @"peer-reviewed"@  (kept as-is)
--     * @published@      → @"published"@
--     * @retracted@      → @"retracted"@
--
--   'noResult' for absent, invalid, or @unreviewed@ values, mirroring
--   'peerStatusField'.
peerStatusDisplayField :: Context String
peerStatusDisplayField = field "peer-status-display" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString "peer-status" meta of
        Nothing -> noResult "no peer-status"
        Just raw ->
            case lookup (map toLower (trim raw)) displayMap of
                Just disp -> return disp
                Nothing   -> noResult "no display form (absent / unreviewed / invalid)"
  where
    displayMap =
        [ ("under-review",   "under review")
        , ("peer-reviewed",  "peer-reviewed")
        , ("published",      "published")
        , ("retracted",      "retracted")
        ]

-- | All epistemic context fields composed.
epistemicCtx :: Context String
epistemicCtx =
    dotsField "importance-dots" "importance"
    <> dotsField "evidence-dots" "evidence"
    <> confidenceField
    <> confidenceProvedField
    <> peerStatusField
    <> peerStatusDisplayField
    <> overallScoreField
    <> confidenceTrendField
    <> stabilityField
    <> lastReviewedField
    <> lastReviewedIsoField
    <> epistemicSvgField

-- ---------------------------------------------------------------------------
-- Essay context
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- Display date (revision-aware)
-- ---------------------------------------------------------------------------

-- | Resolve an item's display date as a 'UTCTime': the most-recent
--   'revisionDateISO' if the item has a 'revised:' entry, else the
--   creation date via 'getItemUTC'. Falls back to the creation date
--   when a revision's ISO string fails to parse.
--
--   Shared by every revision-aware field below and by
--   'recentFirstByDisplay', so they always agree on what the item's
--   display date is.
itemDisplayUTC :: Item a -> Compiler UTCTime
itemDisplayUTC item = do
    meta <- getMetadata (itemIdentifier item)
    case getRevisions meta of
        (r:_) -> case parseTimeM True defaultTimeLocale "%Y-%m-%d"
                                  (revisionDateISO r) :: Maybe UTCTime of
            Just utc -> return utc
            Nothing  -> getItemUTC defaultTimeLocale (itemIdentifier item)
        [] -> getItemUTC defaultTimeLocale (itemIdentifier item)

-- | @$date-display$@ — the date shown next to an item in list renderings.
--   Most-recent revision date if the item has a 'revised:' entry, else
--   its creation date. Formatted "17 April 2026".
dateDisplayField :: Context String
dateDisplayField = field "date-display" $ \item ->
    formatTime defaultTimeLocale "%-d %B %Y" <$> itemDisplayUTC item

-- | @$date-iso$@ — ISO-8601 form of the display date, for
--   @<time datetime="...">@ attributes. Same revision-aware
--   semantics as 'dateDisplayField'.
dateDisplayIsoField :: Context String
dateDisplayIsoField = field "date-iso" $ \item ->
    formatTime defaultTimeLocale "%Y-%m-%d" <$> itemDisplayUTC item

-- | @$date-original$@ — the item's creation date, present in the
--   context only when the most-recent revision date differs from it.
--   Consumed by the card partial's "· revised from …" annotation.
--   'noResult' otherwise (so the annotation is simply absent for
--   never-revised items).
dateOriginalField :: Context String
dateOriginalField = field "date-original" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case getRevisions meta of
        [] -> noResult "no revisions"
        (r:_) -> do
            created <- getItemUTC defaultTimeLocale (itemIdentifier item)
            let createdIso = formatTime defaultTimeLocale "%Y-%m-%d" created
            if revisionDateISO r == createdIso
                then noResult "revision date equals creation date"
                else return (formatTime defaultTimeLocale "%-d %B %Y" created)

-- | @$revision-note$@ — prose note attached to the most-recent
--   'revised:' entry, if any. Rendered as an italicized line under
--   the abstract on the item card. 'noResult' when there's no
--   revision, or when the most-recent revision has no note.
revisionNoteField :: Context String
revisionNoteField = field "revision-note" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case getRevisions meta of
        (r:_) | Just note <- revisionNote r, not (null (trim note)) -> return note
        _ -> noResult "no revision note"

-- | Bundle of revision-aware fields consumed by the item-card partial:
--   @$date-display$@, @$date-iso$@, @$date-original$@, @$revision-note$@.
--   Compose once on any surface that renders item cards.
revisionDateFields :: Context String
revisionDateFields =
       dateDisplayField
    <> dateDisplayIsoField
    <> dateOriginalField
    <> revisionNoteField

-- | Sort items most-recent-first by 'itemDisplayUTC' — same ordering
--   the card shows in its date gutter, so items with recent revisions
--   move to the top without divorcing the sort key from the visible
--   date. Callers: the @/new.html@ rule, 'Tags.applyTagRules', and
--   the library rule.
recentFirstByDisplay :: [Item a] -> Compiler [Item a]
recentFirstByDisplay items = do
    keyed <- mapM (\i -> (,) <$> itemDisplayUTC i <*> pure i) items
    return $ map snd $ sortBy (flip (comparing fst)) keyed

-- ---------------------------------------------------------------------------
-- Revised: frontmatter schema
-- ---------------------------------------------------------------------------

-- | A single entry from a @revised:@ frontmatter list. Exposed so
--   downstream Phase-5 consumers (the 'dateDisplayField' implementation
--   and the revision-annotation fields on the item card) can all read
--   the same canonical form.
data Revision = Revision
    { revisionDateISO :: String        -- ^ ISO-8601 date, e.g. "2026-04-10"
    , revisionNote    :: Maybe String  -- ^ optional prose note for the entry
    }

-- | Parse and normalize the @revised:@ frontmatter field into a list
--   of 'Revision' entries, sorted most-recent-first (ISO @YYYY-MM-DD@
--   strings sort lexicographically in chronological order, so
--   reverse-sorting them yields most-recent-first).
--
--   Accepted frontmatter shapes:
--
--   @
--   -- Scalar shorthand (normalized to one entry with no note)
--   revised: "2026-04-10"
--
--   -- Canonical list of objects
--   revised:
--     - date: "2026-04-10"
--       note: "expanded §3 on Shestov"
--     - date: "2025-12-03"              -- note optional per-entry
--   @
--
--   The two shapes normalize to the same list-of-'Revision' form here.
--   No other site code should branch on the frontmatter shape —
--   everything downstream reads this function's output.
--
--   Entries that fail to parse (missing @date:@, non-string values,
--   unexpected types) are silently dropped rather than erroring the
--   whole build; the site still compiles with a malformed @revised:@.
getRevisions :: Metadata -> [Revision]
getRevisions meta =
    sortBy (flip (comparing revisionDateISO)) $
    case KM.lookup "revised" meta of
        Just (String t) -> [Revision (T.unpack t) Nothing]
        Just (Array v)  -> mapMaybe parseEntry (V.toList v)
        _               -> []
  where
    parseEntry (Object o) = do
        d <- getString =<< KM.lookup "date" o
        return (Revision d (getString =<< KM.lookup "note" o))
    parseEntry _ = Nothing

    getString (String t) = Just (T.unpack t)
    getString _          = Nothing

essayCtx :: Context String
essayCtx =
    authorLinksField
    <> affiliationField
    <> snapshotField "toc"          "toc"
    <> snapshotField "word-count"   "word-count"
    <> snapshotField "reading-time" "reading-time"
    <> bibliographyField
    <> furtherReadingField
    <> backlinksField
    <> similarLinksField
    <> epistemicCtx
    <> versionHistoryField
    <> versionHistoryPrimaryField
    <> versionHistoryRestField
    <> versionHistoryRangeField
    <> versionHistoryRangeStartField
    <> versionHistoryRangeEndField
    <> versionHistoryCommitsField
    <> dateField "date-created" "%-d %B %Y"
    <> dateField "date-modified" "%-d %B %Y"
    <> revisionDateFields
    <> constField "math" "true"
    <> tagLinksField "essay-tags"
    <> keywordLinksField "essay-keywords"
    <> siteCtx

-- ---------------------------------------------------------------------------
-- Post context
-- ---------------------------------------------------------------------------

postCtx :: Context String
postCtx =
    authorLinksField
    <> affiliationField
    <> backlinksField
    <> similarLinksField
    <> dateField "date"     "%-d %B %Y"
    <> dateField "date-iso" "%Y-%m-%d"
    <> constField "math" "true"
    -- Blog posts can opt in to the epistemic figure / chips by setting
    -- the relevant frontmatter fields. The Marks module's epistemic SVG
    -- field returns 'noResult' when @status:@ is absent, so unstatused
    -- posts render unchanged. The dot / strip fields below mirror the
    -- essay context so a status-bearing post gets the same chips.
    <> dotsField "importance-dots" "importance"
    <> dotsField "evidence-dots" "evidence"
    <> confidenceField
    <> confidenceProvedField
    <> peerStatusField
    <> peerStatusDisplayField
    <> overallScoreField
    <> confidenceTrendField
    <> stabilityField
    <> lastReviewedField
    <> lastReviewedIsoField
    <> epistemicSvgField
    <> siteCtx

-- ---------------------------------------------------------------------------
-- Page context
-- ---------------------------------------------------------------------------

pageCtx :: Context String
pageCtx = authorLinksField <> affiliationField <> siteCtx

-- ---------------------------------------------------------------------------
-- Reading contexts (fiction + poetry)
-- ---------------------------------------------------------------------------

-- | Base reading context: essay fields + the "reading" flag (activates
--   reading.css / reading.js via head.html and body class via default.html).
readingCtx :: Context String
readingCtx = essayCtx <> constField "reading" "true"

-- | Poetry context: reading mode + "poetry" flag for CSS body class.
poetryCtx :: Context String
poetryCtx = readingCtx <> constField "poetry" "true"

-- | Fiction context: reading mode + "fiction" flag for CSS body class.
fictionCtx :: Context String
fictionCtx = readingCtx <> constField "fiction" "true"

-- ---------------------------------------------------------------------------
-- Composition context (music landing pages + score reader)
-- ---------------------------------------------------------------------------

data Movement = Movement
    { movName     :: String
    , movPage     :: Int
    , movDuration :: String
    , movAudio    :: Maybe String
      -- | Offset of this movement into the composition's full @recording@,
      --   normalised to whole seconds. Parsed and carried through the
      --   context now so the schema is settled before any composition
      --   exists; no template consumes it yet.
    , movTime     :: Maybe Int
    }

-- | A movement together with the URLs its template row needs.
--
--   Inside @$for(movements)$@ a field lookup resolves against the movement
--   sub-context /alone/ — the composition's own fields (@$slug$@,
--   @$has-score$@, @$score-url$@) are not in scope there. Anything a
--   movement row needs from its parent must therefore be resolved while
--   building the list and carried in, which is what this wrapper is for.
data MovementView = MovementView
    { mvMovement :: Movement
    , mvScoreUrl :: Maybe String   -- ^ deep link into the reader at this movement
    , mvAudioUrl :: Maybe String   -- ^ absolute URL of this movement's recording
    }

-- | Parse the @movements@ frontmatter key. Returns parsed movements and a
--   list of human-readable warnings for any entries that failed to parse.
--   Callers can surface the warnings via 'unsafeCompiler' so silent typos
--   don't strip movements without diagnostic.
--
--   A movement is dropped only when a /required/ field (name, page,
--   duration) is missing. A malformed optional @time@ warns but keeps the
--   movement — losing a whole movement over a mistyped timecode would be
--   a worse failure than ignoring the timecode.
parseMovementsWithWarnings :: Metadata -> ([Movement], [String])
parseMovementsWithWarnings meta =
    case KM.lookup "movements" meta of
        Just (Array v) ->
            let results = zipWith parseIndexed [1 :: Int ..] (V.toList v)
            in  ( [m | (Just m, _) <- results]
                , concatMap snd results
                )
        _ -> ([], [])
  where
    parseIndexed i (Object o) =
        case mkMovement o of
            Nothing -> (Nothing, [missingRequired i])
            Just mk ->
                let raw    = KM.lookup "time" o
                    parsed = raw >>= scalarText >>= parseTimecode
                in  case (raw, parsed) of
                        (Just _, Nothing) -> (Just (mk Nothing),  [badTime i])
                        _                 -> (Just (mk parsed), [])
    parseIndexed i _ = (Nothing, [missingRequired i])

    missingRequired i =
        "movement #" ++ show i ++ " is missing a required field "
        ++ "(name, page, or duration) — entry skipped"

    badTime i =
        "movement #" ++ show i ++ " has an unparseable time: — expected "
        ++ "H:MM:SS, M:SS, or a plain second count; offset ignored"

    -- Every field but the time offset, which 'parseIndexed' applies so a
    -- bad timecode can warn without discarding the movement.
    mkMovement o = Movement
        <$> (getString =<< KM.lookup "name"     o)
        <*> (getInt    =<< KM.lookup "page"     o)
        <*> (getString =<< KM.lookup "duration" o)
        <*> pure (getString =<< KM.lookup "audio" o)

    getString (String t) = Just (T.unpack t)
    getString _          = Nothing

    getInt (Number n) = Just (floor (fromRational (toRational n) :: Double))
    getInt _          = Nothing

-- | A YAML scalar as text, so @time: "3:41"@ and @time: 221@ both reach
--   'parseTimecode' by the same route.
scalarText :: Value -> Maybe String
scalarText (String t) = Just (T.unpack t)
scalarText (Number n) =
    Just (show (floor (fromRational (toRational n) :: Double) :: Int))
scalarText _          = Nothing

-- | Parse a recording offset to whole seconds. Accepts @H:MM:SS@, @M:SS@,
--   or a plain second count. Normalising at build time keeps author-facing
--   time formats out of the reader's JavaScript entirely.
parseTimecode :: String -> Maybe Int
parseTimecode s =
    case (traverse readMaybe parts :: Maybe [Int]) of
        Just [sec]       -> Just sec
        Just [m, sec]    -> Just (m * 60 + sec)
        Just [h, m, sec] -> Just (h * 3600 + m * 60 + sec)
        _                -> Nothing
  where
    parts = map T.unpack (T.splitOn ":" (T.pack (trim s)))

parseMovements :: Metadata -> [Movement]
parseMovements = fst . parseMovementsWithWarnings

-- | Extract the composition slug from an item's identifier.
--   "content/music/symphonic-dances/index.md" → "symphonic-dances"
compSlug :: Item a -> String
compSlug = takeFileName . takeDirectory . toFilePath . itemIdentifier

-- | Whether a composition declares a score at all — either an explicit
--   @score-pages@ list or a @score-dir@ to be globbed.
--
--   Metadata-only by necessity: 'Site.rules' consults this through
--   'matchMetadata' at rule-generation time, where the 'Compiler' monad
--   (and so 'getMatches') does not exist yet. A @score-dir@ naming an
--   empty directory therefore still routes a reader page; 'scorePageList'
--   is the authority on which pages actually exist, and @$has-score$@
--   goes through it.
declaresScore :: Metadata -> Bool
declaresScore meta =
    not (null (fromMaybe [] (lookupStringList "score-pages" meta)))
    || maybe False (not . null . trim) (lookupString "score-dir" meta)

-- | A composition's score pages as source-relative paths, in reading order.
--
--   An explicit @score-pages@ list wins when present — it is the escape
--   hatch for an order no filename convention can express. Otherwise
--   @score-dir@ is globbed through 'getMatches', which registers a real
--   Hakyll dependency, so dropping a page into the directory triggers a
--   rebuild. Hand-listing sixty orchestral pages is not viable, and a
--   hand-list that falls out of sync with the directory fails silently.
scorePageList :: Item a -> Compiler [FilePath]
scorePageList item = do
    meta <- getMetadata (itemIdentifier item)
    let explicit = fromMaybe [] (lookupStringList "score-pages" meta)
    if not (null explicit)
        then return explicit
        else case fmap trim (lookupString "score-dir" meta) of
            Just dir | not (null dir) -> do
                let srcDir = takeDirectory (toFilePath (itemIdentifier item))
                ids <- getMatches (fromGlob (srcDir </> dir </> "*.svg"))
                return $ sortBy compareNatural
                    [ makeRelative srcDir (toFilePath i) | i <- ids ]
            _ -> return []

-- | Filename ordering that compares digit runs numerically, so
--   @page-2.svg@ sorts before @page-10.svg@ whether or not the author
--   zero-padded. Plain lexicographic order silently interleaves the pages
--   of any unpadded score — a failure that reads as an engraving mistake
--   rather than a build one. The raw path breaks ties, so the ordering is
--   total even when padding makes two names numerically equal.
-- | The width-to-height ratio of an SVG, as a bare decimal. A plain
--   number rather than an @aspect-ratio@ pair because the stylesheet needs
--   it in @calc()@ too — deriving the fit-to-height width from the viewport
--   is what lets the reader size a page correctly before its script runs.
--   Prefers @viewBox@; falls back to the @width@ and
--   @height@ attributes, whose ratio needs no unit conversion because both
--   carry the same unit (@279.4mm@ / @215.9mm@ is as usable as a viewBox).
--
--   Only the head of the file is scanned: the root element's attributes are
--   the first thing in the document, and a sixty-page orchestral score is
--   not worth reading into memory to learn its page shape.
svgAspect :: FilePath -> IO (Maybe String)
svgAspect path = do
    r <- try (TIO.readFile path) :: IO (Either IOException T.Text)
    return $ case r of
        Left _     -> Nothing
        Right body -> ratioOf (T.take 2048 body)
  where
    ratioOf head' =
        case viewBoxRatio head' of
            Just x  -> Just x
            Nothing -> do
                w <- number =<< attrValue " width" head'
                h <- number =<< attrValue " height" head'
                format w h

    viewBoxRatio head' = do
        vb <- attrValue "viewBox" head'
        case mapMaybe number (T.words (T.map commaToSpace vb)) of
            [_, _, w, h] -> format w h
            _            -> Nothing

    commaToSpace c = if c == ',' then ' ' else c

    format w h
        | w > 0 && h > 0 = Just (showFFloat' (w / h))
        | otherwise      = Nothing

    -- 4 decimals is finer than any display can resolve and keeps the
    -- generated attribute short.
    showFFloat' x = show (fromIntegral (round (x * 10000) :: Integer) / 10000
                            :: Double)

    -- Leading numeric run of an attribute value, so "279.4mm" parses.
    number t =
        let (digits, _) = T.span (\c -> isDigit c || c == '.' || c == '-') (T.strip t)
        in  if T.null digits then Nothing
                             else readMaybe (T.unpack digits) :: Maybe Double

-- | The value of an XML attribute, found by literal scan. @name@ should
--   carry its own leading space where the bare name would otherwise match a
--   longer one (@\" width\"@ must not match @stroke-width@).
attrValue :: T.Text -> T.Text -> Maybe T.Text
attrValue name body =
    let (_, rest) = T.breakOn (name <> "=\"") body
    in  if T.null rest
            then Nothing
            else let v          = T.drop (T.length name + 2) rest
                     (val, end) = T.breakOn "\"" v
                 in  if T.null end then Nothing else Just val

compareNatural :: FilePath -> FilePath -> Ordering
compareNatural = comparing (\path -> (chunks path, path))
  where
    chunks :: String -> [Either Integer String]
    chunks [] = []
    chunks cs@(c : _)
        | isDigit c = let (d, r) = span  isDigit cs in Left  (read d)          : chunks r
        | otherwise = let (t, r) = break isDigit cs in Right (map toLower t) : chunks r

-- | Context for music composition landing pages and the score reader.
--   Extends essayCtx with composition-specific fields:
--     $slug$             — URL slug (e.g. "symphonic-dances")
--     $score-url$        — absolute URL of the score reader page
--     $has-score$        — present when the composition resolves to >=1 page
--     $score-page-count$ — total number of score pages
--     $score-pages$      — list of {score-page-url} items
--     $first-score-page$ — URL of page 1, for the scripting-off fallback
--     $score-aspect$     — page 1's width/height as a bare decimal
--     $score-portrait$   — present when page 1 is taller than it is wide
--     $has-movements$    — present when movements frontmatter is non-empty
--     $movements$        — list of {movement-name, movement-page,
--                            movement-duration, movement-time, has-audio,
--                            movement-audio-url, movement-score-url}
--   All other frontmatter keys (instrumentation, duration, premiere,
--   commissioned-by, pdf, abstract, etc.) are available via defaultContext.
compositionCtx :: Context String
compositionCtx =
    constField "composition" "true"
    <> slugField
    <> scoreUrlField
    <> hasScoreField
    <> scorePageCountField
    <> scorePagesListField
    <> firstScorePageField
    <> scoreAspectField
    <> scorePortraitField
    <> hasMovementsField
    <> movementsListField
    <> essayCtx
  where
    slugField = field "slug" (return . compSlug)

    scoreUrlField = field "score-url" $ \item ->
        return $ "/music/" ++ compSlug item ++ "/score/"

    -- All four score fields resolve through 'scorePageList', so an
    -- explicit list and a globbed directory behave identically and
    -- @$has-score$@ can never disagree with @$score-page-count$@.
    hasScoreField = field "has-score" $ \item -> do
        pages <- scorePageList item
        if null pages then noResult "no score pages" else return "true"

    scorePageCountField = field "score-page-count" $ \item ->
        show . length <$> scorePageList item

    scorePagesListField = listFieldWith "score-pages" spCtx $ \item -> do
        let base = "/music/" ++ compSlug item ++ "/"
        pages <- scorePageList item
        return $ map (\p -> Item (fromFilePath p) (base ++ p)) pages
      where
        spCtx = field "score-page-url" (return . itemBody)

    -- Page 1's URL, so the template can render it into the markup instead
    -- of leaving an empty src for JavaScript to fill: that is what makes
    -- the reader show a score with scripting off, paint the first page
    -- without waiting on a fetch, and reserve its box before layout.
    firstScorePageField = field "first-score-page" $ \item -> do
        pages <- scorePageList item
        case pages of
            (p : _) -> return $ "/music/" ++ compSlug item ++ "/" ++ p
            []      -> noResult "no score pages"

    -- Present when page 1 is taller than it is wide. Portrait pages default
    -- to fit-width rather than fit-height: a portrait sheet in a landscape
    -- window leaves most of the screen empty at fit-height, and on a
    -- large-ensemble score that shrinks the staves past readability. A
    -- 33-stave concert band page is legible at fit-width and is not at
    -- fit-height; a 13-stave landscape page is legible at either.
    scorePortraitField = field "score-portrait" $ \item -> do
        pages <- scorePageList item
        case pages of
            []      -> noResult "no score pages"
            (p : _) -> do
                let srcDir = takeDirectory (toFilePath (itemIdentifier item))
                aspect <- unsafeCompiler (svgAspect (srcDir </> p))
                case aspect >>= (readMaybe :: String -> Maybe Double) of
                    Just r | r < 1 -> return "true"
                    _              -> noResult "page 1 is not portrait"

    -- The sheet's shape, read from page 1 at build time so its box is
    -- reserved before anything loads. That removes the first-paint layout
    -- shift for everyone, and gives the scripting-off fallback a correctly
    -- proportioned page instead of the stylesheet's generic portrait
    -- default.
    --
    -- Read through 'unsafeCompiler' rather than 'load': score pages are
    -- copied byte-for-byte by 'copyFileCompiler', so no String item exists
    -- to depend on. 'scorePageList' registers the directory glob, so adding
    -- or removing pages rebuilds this — but re-exporting the same filenames
    -- at a different page size does not, and needs a clean build to show up.
    scoreAspectField = field "score-aspect" $ \item -> do
        pages <- scorePageList item
        case pages of
            []      -> noResult "no score pages"
            (p : _) -> do
                let srcDir = takeDirectory (toFilePath (itemIdentifier item))
                aspect <- unsafeCompiler (svgAspect (srcDir </> p))
                maybe (noResult "page 1 declares no usable dimensions")
                      return aspect

    hasMovementsField = field "has-movements" $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        if null (parseMovements meta) then noResult "no movements" else return "true"

    movementsListField = listFieldWith "movements" movCtx $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        pageCount <- length <$> scorePageList item
        let (mvs, warnings) = parseMovementsWithWarnings meta
            ident = toFilePath (itemIdentifier item)
            -- `page` indexes the reader (1..n), not the printed folio. The
            -- two diverge the moment a score has front matter, and the only
            -- symptom is a movement button that jumps to the wrong place —
            -- so an out-of-range page is worth saying out loud.
            outOfRange =
                [ "movement \"" ++ movName mv ++ "\" starts at page "
                  ++ show (movPage mv) ++ ", but the score has "
                  ++ show pageCount ++ " page(s) — `page:` is the reader's "
                  ++ "1-based index, not the printed page number"
                | pageCount > 0, mv <- mvs
                , movPage mv < 1 || movPage mv > pageCount
                ]
        unsafeCompiler $ mapM_
            (\w -> putStrLn $ "[Movements] " ++ ident ++ ": " ++ w)
            (warnings ++ outOfRange)
        let slug = compSlug item
            viewOf m = MovementView
                { mvMovement = m
                , mvScoreUrl =
                    if pageCount > 0
                        then Just $ "/music/" ++ slug ++ "/score/?p="
                                     ++ show (movPage m)
                        else Nothing
                , mvAudioUrl =
                    (\a -> "/music/" ++ slug ++ "/" ++ a) <$> movAudio m
                }
        return $ zipWith
            (\idx m -> Item (fromFilePath ("mv" ++ show (idx :: Int))) (viewOf m))
            [1..] mvs
      where
        movCtx =
            field "movement-name"        (return . movName     . mvOf)
            <> field "movement-page"     (return . show . movPage . mvOf)
            <> field "movement-duration" (return . movDuration . mvOf)
            <> field "movement-time"
                (\i -> maybe (noResult "no time offset") (return . show)
                             (movTime (mvOf i)))
            <> field "movement-audio-url"
                (\i -> maybe (noResult "no audio") return (mvAudioUrl (itemBody i)))
            <> field "has-audio"
                (\i -> maybe (noResult "no audio") (const (return "true"))
                             (mvAudioUrl (itemBody i)))
            <> field "movement-score-url"
                (\i -> maybe (noResult "no score") return (mvScoreUrl (itemBody i)))
          where
            mvOf = mvMovement . itemBody

-- ---------------------------------------------------------------------------
-- Photography context
-- ---------------------------------------------------------------------------

-- | Extract the photo entry's slug from its identifier.
--
--   * Flat single   @content/photography/<slug>.md@      → @<slug>@
--   * Directory     @content/photography/<slug>/index.md@ → @<slug>@
--
--   The slug is the URL segment under @/photography/@ and the directory
--   name into which co-located assets (the photo, future EXIF + palette
--   sidecars) are copied by the asset rule.
photoSlug :: Item a -> String
photoSlug item =
    let fp     = toFilePath (itemIdentifier item)
        fname  = takeFileName fp
    in  if fname == "index.md"
        then takeFileName (takeDirectory fp)
        else takeWhile (/= '.') fname

-- ---------------------------------------------------------------------------
-- Sidecar reader (Phase 3)
-- ---------------------------------------------------------------------------
--
-- @{photo}.exif.yaml@ and @{photo}.palette.yaml@ are produced by the
-- Python tools at @make build@ time (see @tools/extract-exif.py@ and
-- @tools/extract-palette.py@). They live alongside the photo file
-- under @content/photography/<slug>/@ and back-fill metadata that the
-- author chose not to write in frontmatter.
--
-- Read strategy: 'unsafeCompiler' + 'doesFileExist'. Sidecars are NOT
-- registered as Hakyll items, so this read bypasses the dependency
-- tracker. That is acceptable because:
--
--   * The Python tools always run before @cabal run site -- build@
--     (the Makefile orders them that way).
--   * Re-running the EXIF / palette extractor invalidates only those
--     fields' rendered output; rebuilding @make build@ from scratch
--     covers the dependency-edge case for free.
--
-- Resolution rule for every sidecar-backed field: frontmatter wins;
-- if frontmatter is absent OR empty, fall back to sidecar; if neither
-- supplies a value, return 'noResult' so the consuming template's
-- @$if(...)$@ guard suppresses the row.

-- | Compute the sidecar path for a photo entry.
--
--   @suffix@ is @".exif.yaml"@ or @".palette.yaml"@.
--   Returns @Nothing@ when the entry has no @photo:@ frontmatter or
--   when the entry is flat-form (no co-located asset directory).
photoSidecarPath :: String -> Item a -> Compiler (Maybe FilePath)
photoSidecarPath suffix item = do
    meta <- getMetadata (itemIdentifier item)
    let fp      = toFilePath (itemIdentifier item)
        isFlat  = takeDirectory fp == "content/photography"
    -- Same test as photoUrlField, and for the same reason: what matters is
    -- whether the entry has a co-located asset directory, which is true of
    -- directory-form singles AND series children. Gating on index.md meant
    -- series children resolved no sidecar at all — so every photograph in a
    -- series silently lost its width and height attributes, and with them
    -- the layout-shift protection those exist to provide.
    case (isFlat, lookupString "photo" meta) of
        (False, Just photo) | not (null photo) ->
            return $ Just $ takeDirectory fp </> photo ++ suffix
        _ -> return Nothing

-- | Load a sidecar YAML file as an Aeson Object (same shape Hakyll
--   uses for frontmatter). Returns 'Aeson.empty' when the file is
--   missing or fails to parse — sidecars are advisory, never fatal.
loadSidecar :: FilePath -> IO Aeson.Object
loadSidecar path = do
    exists <- doesFileExist path
    if not exists
        then return KM.empty
        else do
            decoded <- Y.decodeFileEither path
            case decoded of
                Right (Object obj) -> return obj
                _                  -> return KM.empty

-- | Read a sidecar object for a given suffix. Returns the empty object
--   when the entry has no resolvable sidecar path or when the file is
--   absent / malformed.
readPhotoSidecar :: String -> Item a -> Compiler Aeson.Object
readPhotoSidecar suffix item = do
    mPath <- photoSidecarPath suffix item
    case mPath of
        Nothing   -> return KM.empty
        Just path -> unsafeCompiler (loadSidecar path)

-- | Coerce a YAML scalar value to a plain String for template
--   interpolation. Integers render without a trailing @.0@; structures
--   and arrays return 'Nothing' (callers needing those should branch
--   on 'Value' directly).
yamlAsString :: Value -> Maybe String
yamlAsString (String t) =
    let s = T.unpack t
    in  if null (trim s) then Nothing else Just (trim s)
yamlAsString (Number n) =
    case Sci.floatingOrInteger n :: Either Double Integer of
        Right i -> Just (show i)
        Left  d -> Just (show d)
yamlAsString _ = Nothing

-- | Look up a key in a sidecar object, coercing scalar values to
--   String. Returns 'Nothing' for missing keys, empty strings, and
--   structural values (arrays / nested objects).
sidecarLookupString :: String -> Aeson.Object -> Maybe String
sidecarLookupString key obj = yamlAsString =<< KM.lookup (AK.fromString key) obj

-- | Generic frontmatter > EXIF-sidecar fallback field.
--
--   @key@ is the YAML key — same name on both sides. Frontmatter
--   wins when present and non-empty; otherwise the matching key in
--   @{photo}.exif.yaml@. 'noResult' fires when neither supplies a
--   value, so the consuming template's @$if(key)$@ guard suppresses
--   the row.
exifBackedField :: String -> Context String
exifBackedField key = field key $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    case lookupString key meta of
        Just v | not (null (trim v)) -> return (trim v)
        _ -> do
            obj <- readPhotoSidecar ".exif.yaml" item
            case sidecarLookupString key obj of
                Just v  -> return v
                Nothing -> noResult ("no " ++ key ++ " in frontmatter or EXIF sidecar")

-- | Canonical URL for a known license name.
--
--   The frontmatter @license:@ string is normalized — lowercased, with
--   internal whitespace collapsed — before lookup, so any of these all
--   resolve identically:
--
--     * @"CC BY-SA 4.0"@
--     * @"cc by-sa 4.0"@
--     * @"  CC  BY-SA   4.0  "@
--
--   For licenses not in this table (e.g. a custom license, or "All
--   Rights Reserved" which has no URL), the author can supply their
--   own @license-url:@ frontmatter field; the field-level resolver
--   (@licenseUrlField@) prefers explicit @license-url@ and falls back
--   to this lookup only when the author hasn't provided one.
canonicalLicenseUrl :: String -> Maybe String
canonicalLicenseUrl raw =
    case unwords (words (map (\c -> if c == '_' then ' ' else toLowerC c) raw)) of
        "cc by 4.0"        -> Just "https://creativecommons.org/licenses/by/4.0/"
        "cc by-sa 4.0"     -> Just "https://creativecommons.org/licenses/by-sa/4.0/"
        "cc by-nc 4.0"     -> Just "https://creativecommons.org/licenses/by-nc/4.0/"
        "cc by-nc-sa 4.0"  -> Just "https://creativecommons.org/licenses/by-nc-sa/4.0/"
        "cc by-nd 4.0"     -> Just "https://creativecommons.org/licenses/by-nd/4.0/"
        "cc by-nc-nd 4.0"  -> Just "https://creativecommons.org/licenses/by-nc-nd/4.0/"
        "cc0"              -> Just "https://creativecommons.org/publicdomain/zero/1.0/"
        "cc0 1.0"          -> Just "https://creativecommons.org/publicdomain/zero/1.0/"
        "public domain"    -> Just "https://creativecommons.org/publicdomain/mark/1.0/"
        _                  -> Nothing
  where
    toLowerC c
        | c >= 'A' && c <= 'Z' = toEnum (fromEnum c + 32)
        | otherwise            = c

-- | Context for photography pages and photo cards.
--
--   Phase 1: frontmatter-only. Auto-extracted EXIF + palette sidecars
--   land in Phase 3, where this context will gain a merge step that
--   reads @{photo}.exif.yaml@ / @{photo}.palette.yaml@ and exposes
--   their fields under the same template variables. Frontmatter wins.
--
--   Photography pages do not include the essay context's epistemic,
--   bibliography, backlinks, similar-links, TOC, word-count, or
--   reading-time fields — none of those apply to visual content. See
--   @PHOTOGRAPHY.md@ for the design rationale.
--
--   Exposed template variables:
--     @$photography$@   — flag, gates @photography.css@ in head.html
--                         and the @data-page-type@ body attribute used
--                         by the Phase 2 darkroom-mode lightbox
--     @$slug$@          — URL slug under @/photography/@
--     @$photo-url$@     — absolute URL of the photo file. Built as
--                         @/photography/<dir>/<photo>@ for any entry with
--                         a co-located image — directory-form singles and
--                         series children alike; @noResult@ for flat
--                         singles (templates use the @photo@
--                         frontmatter directly there).
--     @$captured-display$@, @$captured-iso$@ — capture date in
--                         human-readable and ISO forms; @noResult@
--                         when @captured:@ is absent. Distinct from
--                         the publication @date:@ shown in card lists.
--     @$photography-tags$@ — listField of @{tag-name, tag-url}@.
--     @$palette-swatches$@ — listField of @{swatch}@ (hex string).
--                         @noResult@ when the @palette:@ frontmatter
--                         is absent or empty so the template's
--                         @$if(palette-swatches)$@ gate suppresses an
--                         empty strip.
photographyCtx :: Context String
photographyCtx =
    constField "photography" "true"
    <> slugField
    <> photoUrlField
    <> photoWebpUrlField
    -- EXIF-backed fields. Each prefers frontmatter and falls back to
    -- @{photo}.exif.yaml@ produced by @tools/extract-exif.py@. Sidecars
    -- absent on film scans (no EXIF on a film negative) is fine —
    -- noResult propagates and the template's @$if(...)$@ gate hides
    -- the row.
    <> exifBackedField "camera"
    <> exifBackedField "lens"
    <> exifBackedField "exposure"
    <> exifBackedField "shutter"
    <> exifBackedField "aperture"
    <> exifBackedField "iso"
    <> exifBackedField "focal-length"
    -- Pixel dimensions for CLS-prevention width/height attrs on every
    -- <img>. Read from the EXIF sidecar produced by extract-exif.py;
    -- frontmatter wins if the author wants to override (e.g., to
    -- declare a different rendered size).
    <> exifBackedField "width"
    <> exifBackedField "height"
    <> capturedDisplayField
    <> capturedIsoField
    <> paletteSwatchesField
    <> licenseUrlField
    <> photoLinksField
    -- Backlinks. A photograph is a link *target* like any other page: a
    -- poem or essay that references the frame produces an entry keyed to
    -- this page's URL, and the join is symmetric because both sides go
    -- through 'Backlinks.normaliseUrl'. Photography stays out of
    -- 'Patterns.allContent' — that governs link *sources*, and
    -- caption-scale entries have no outbound prose to contribute.
    <> backlinksField
    <> tagLinksField "photography-tags"
    <> authorLinksField
    <> affiliationField
    <> dateField "date"     "%-d %B %Y"
    <> dateField "date-iso" "%Y-%m-%d"
    <> revisionDateFields
    <> siteCtx
  where
    slugField :: Context String
    slugField = field "slug" (return . photoSlug)

    -- Build @/photography/<slug>/<photo>@ when both the directory-form
    -- entry and a @photo:@ frontmatter key are present. Flat singles
    -- have no co-located asset directory, so @noResult@ there — the
    -- template falls back to interpreting the @photo:@ frontmatter
    -- as a literal URL.
    -- The test is "does this entry have a co-located asset directory", which
    -- is true of BOTH directory-form singles (<slug>/index.md) and series
    -- children (<series>/<photo>.md) — the latter keep their image beside
    -- their markdown, in the series directory. Gating on index.md alone sent
    -- series children down the flat-single fallback, where the template used
    -- the bare `photo:` filename as a URL; since a child page is served from
    -- <series>/<photo>/, that resolved one directory too deep and 404'd.
    --
    -- photoSlug is deliberately not reused here: for a non-index.md file it
    -- returns the file's own basename, whereas the image lives under the
    -- containing directory's name.
    photoUrlField :: Context String
    photoUrlField = field "photo-url" $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        let fp      = toFilePath (itemIdentifier item)
            isFlat  = takeDirectory fp == "content/photography"
            dirName = takeFileName (takeDirectory fp)
        case (isFlat, lookupString "photo" meta) of
            (False, Just photo) | not (null photo) ->
                return $ "/photography/" ++ dirName ++ "/" ++ photo
            _ -> noResult "no co-located photo (flat single, or photo: key absent)"

    -- WebP companion URL, mirroring 'photoUrlField'. Returns 'noResult'
    -- when the @.webp@ companion doesn't exist on disk at compile time
    -- (cwebp not installed, conversion not yet run, or this image
    -- failed to convert) so the template's @$if(photo-webp-url)$@
    -- guard suppresses the @<source>@ — the @<picture>@ then degrades
    -- to a plain @<img>@ on the original-format src. Browsers do NOT
    -- fall back from a 404'd @<source>@ to the nested @<img>@; the
    -- file-existence check at build time is load-bearing.
    photoWebpUrlField :: Context String
    photoWebpUrlField = field "photo-webp-url" $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        let fp      = toFilePath (itemIdentifier item)
            isFlat  = takeDirectory fp == "content/photography"
            dirName = takeFileName (takeDirectory fp)
        case (isFlat, lookupString "photo" meta) of
            (False, Just photo) | not (null photo) -> do
                let entryDir    = takeDirectory fp
                    webpDisk    = entryDir </> photoToWebp photo
                exists <- unsafeCompiler (doesFileExist webpDisk)
                if exists
                    then return $ "/photography/" ++ dirName
                                  ++ "/" ++ photoToWebp photo
                    else noResult "no webp companion on disk"
            _ -> noResult "no co-located photo (flat single, or photo: key absent)"
      where
        -- @photo.jpg@ → @photo.webp@; preserves any path components
        -- the author might have written (rare but harmless).
        photoToWebp :: String -> String
        photoToWebp p =
            let dotIdx = lastDotIndex p
            in  case dotIdx of
                    Just i  -> take i p ++ ".webp"
                    Nothing -> p ++ ".webp"

        lastDotIndex :: String -> Maybe Int
        lastDotIndex s = go (length s - 1)
          where
            go i
                | i < 0          = Nothing
                | s !! i == '/'  = Nothing  -- crossed a path boundary
                | s !! i == '.'  = Just i
                | otherwise      = go (i - 1)

    -- Resolve the @captured:@ ISO date with frontmatter > sidecar
    -- precedence. Centralised so the display and ISO fields stay in
    -- agreement on which source they read from.
    resolveCapturedIso :: Item a -> Compiler (Maybe String)
    resolveCapturedIso item = do
        meta <- getMetadata (itemIdentifier item)
        case lookupString "captured" meta of
            Just v | not (null (trim v)) -> return (Just (trim v))
            _ -> do
                obj <- readPhotoSidecar ".exif.yaml" item
                return (sidecarLookupString "captured" obj)

    -- @captured:@ as "15 March 2026". Reads frontmatter, falls back to
    -- the EXIF sidecar's @captured:@ key. Returns @noResult@ when
    -- absent so @$if(captured-display)$@ gates the metadata row.
    capturedDisplayField :: Context String
    capturedDisplayField = field "captured-display" $ \item -> do
        mIso <- resolveCapturedIso item
        case mIso of
            Nothing -> noResult "no captured date in frontmatter or EXIF sidecar"
            Just iso ->
                case parseTimeM True defaultTimeLocale "%Y-%m-%d" iso
                       :: Maybe UTCTime of
                    Just t  -> return (formatTime defaultTimeLocale "%-d %B %Y" t)
                    Nothing -> noResult "captured date does not parse as YYYY-MM-DD"

    -- ISO form passed through unchanged (after a parse-validate round-trip
    -- so a malformed value in either source doesn't reach the template).
    capturedIsoField :: Context String
    capturedIsoField = field "captured-iso" $ \item -> do
        mIso <- resolveCapturedIso item
        case mIso of
            Nothing -> noResult "no captured date in frontmatter or EXIF sidecar"
            Just iso ->
                case parseTimeM True defaultTimeLocale "%Y-%m-%d" iso
                       :: Maybe UTCTime of
                    Just t  -> return (formatTime defaultTimeLocale "%Y-%m-%d" t)
                    Nothing -> noResult "captured date does not parse as YYYY-MM-DD"

    -- @palette:@ list field. Frontmatter wins; otherwise pull the
    -- list from @{photo}.palette.yaml@ (the @palette:@ key, an array
    -- of hex strings produced by @tools/extract-palette.py@). Each
    -- swatch exposes @$swatch$@.
    paletteSwatchesField :: Context String
    paletteSwatchesField = listFieldWith "palette-swatches" swCtx $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        let fmEntries = fromMaybe [] (lookupStringList "palette" meta)
            fmVisible = filter (not . null . trim) fmEntries
        swatches <- if null fmVisible
            then do
                obj <- readPhotoSidecar ".palette.yaml" item
                case KM.lookup "palette" obj of
                    Just (Array vec) ->
                        return [ trim s
                               | val <- V.toList vec
                               , Just s <- [yamlAsString val]
                               , not (null (trim s)) ]
                    _ -> return []
            else return fmVisible
        if null swatches
            then noResult "no palette swatches in frontmatter or palette sidecar"
            else return $ zipWith
                (\i s -> Item (fromFilePath ("palette-" ++ show i)) s)
                ([0 ..] :: [Int])
                swatches
      where
        swCtx = field "swatch" (return . itemBody)

    -- @$license-url-resolved$@: an explicit @license-url:@ frontmatter
    -- value when present, otherwise a canonical URL looked up from the
    -- @license:@ string for known licenses (CC variants, CC0, public
    -- domain). Returns @noResult@ when neither is set, so
    -- @$if(license-url-resolved)$@ gates the link wrapper.
    --
    -- Frontmatter @license:@ itself flows through @defaultContext@ as
    -- @$license$@; the template renders the license name as link text
    -- and uses @$license-url-resolved$@ as @href@.
    licenseUrlField :: Context String
    licenseUrlField = field "license-url-resolved" $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        case lookupString "license-url" meta of
            Just u | not (null (trim u)) -> return (trim u)
            _ -> case lookupString "license" meta of
                Nothing -> noResult "no license"
                Just l  -> case canonicalLicenseUrl l of
                    Just u  -> return u
                    Nothing -> noResult "license not in canonical lookup"

    -- @links:@ frontmatter — outbound links to other surfaces where
    -- the photograph appears or can be acquired (Wikimedia Commons,
    -- Flickr, exhibition catalog, print-sale page, etc.). Each entry
    -- uses the same @"Name | URL"@ pipe syntax as @authors:@ /
    -- @affiliation:@ — the existing site convention.
    --
    -- Each item exposes @$link-name$@ and @$link-url$@. Entries
    -- without a URL are dropped (no point linking to nothing). Returns
    -- @noResult@ on empty so @$if(photo-links)$@ guards the wrapper.
    photoLinksField :: Context String
    photoLinksField = listFieldWith "photo-links" lkCtx $ \item -> do
        meta <- getMetadata (itemIdentifier item)
        let entries = fromMaybe [] (lookupStringList "links" meta)
            parsed  = filter (not . null . snd) (map parseEntry entries)
        if null parsed
            then noResult "no outbound links"
            else return $ map (Item (fromFilePath "")) parsed
      where
        lkCtx = field "link-name" (return . fst . itemBody)
             <> field "link-url"  (return . snd . itemBody)
        parseEntry s = case break (== '|') s of
            (name, '|' : url) -> (trim name, trim url)
            (name, _)         -> (trim name, "")

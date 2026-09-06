{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
module Compilers
    ( essayCompiler
    , postCompiler
    , pageCompiler
    , poetryCompiler
    , fictionCompiler
    , compositionCompiler
    , photographyCompiler
    , sidecarCompiler
    , readerOpts
    , writerOpts
    ) where

import           Hakyll
import           Text.Pandoc.Definition     (Pandoc (..), Block (..),
                                             Inline (..))
import           Text.Pandoc.Options        (ReaderOptions (..), WriterOptions (..),
                                             HTMLMathMethod (..))
import           Text.Pandoc.Extensions     (enableExtension, Extension (..))
import qualified Data.Text                  as T
import           Control.Monad              (forM_, void)
import           Data.Char                  (toLower)
import           Data.Maybe                 (fromMaybe)
import           System.FilePath            (takeDirectory)
import           Utils                      (wordCount, readingTime, escapeHtml)
import           Filters                    (applyAll, preprocessSource)
import qualified Citations
import qualified Filters.Headings           as Headings
import qualified Filters.Score              as Score
import qualified Filters.Viz               as Viz

-- ---------------------------------------------------------------------------
-- Reader / writer options
-- ---------------------------------------------------------------------------

readerOpts :: ReaderOptions
readerOpts = defaultHakyllReaderOptions

-- | Reader options with hard_line_breaks enabled — every source newline within
--   a paragraph becomes a <br>. Used for poetry so stanza lines render as-is.
poetryReaderOpts :: ReaderOptions
poetryReaderOpts = readerOpts
    { readerExtensions = enableExtension Ext_hard_line_breaks
                            (readerExtensions readerOpts) }

writerOpts :: WriterOptions
writerOpts = defaultHakyllWriterOptions
    { writerHTMLMathMethod  = KaTeX ""
    , writerHighlightStyle  = Nothing
    , writerNumberSections  = False
    , writerTableOfContents = False
    }

-- ---------------------------------------------------------------------------
-- Inline stringification (local, avoids depending on Text.Pandoc.Shared)
-- ---------------------------------------------------------------------------

-- | Frontmatter booleans arrive as strings; accept the spellings YAML
--   users reach for and treat anything else as unset.
parseBool :: String -> Maybe Bool
parseBool v = case map toLower v of
    "true"  -> Just True
    "yes"   -> Just True
    "1"     -> Just True
    "false" -> Just False
    "no"    -> Just False
    "0"     -> Just False
    _       -> Nothing

stringify :: [Inline] -> T.Text
stringify = T.concat . map inlineToText
  where
    inlineToText (Str t)           = t
    inlineToText Space             = " "
    inlineToText SoftBreak         = " "
    inlineToText LineBreak         = " "
    inlineToText (Emph ils)        = stringify ils
    inlineToText (Strong ils)      = stringify ils
    inlineToText (Strikeout ils)   = stringify ils
    inlineToText (Superscript ils) = stringify ils
    inlineToText (Subscript ils)   = stringify ils
    inlineToText (SmallCaps ils)   = stringify ils
    inlineToText (Quoted _ ils)    = stringify ils
    inlineToText (Cite _ ils)      = stringify ils
    inlineToText (Code _ t)        = t
    inlineToText (RawInline _ t)   = t
    inlineToText (Link _ ils _)    = stringify ils
    inlineToText (Image _ ils _)   = stringify ils
    inlineToText (Note _)          = ""
    inlineToText (Span _ ils)      = stringify ils
    inlineToText _                 = ""

-- ---------------------------------------------------------------------------
-- TOC extraction
-- ---------------------------------------------------------------------------

-- | Collect (level, identifier, title-text) for h2/h3 headings.
collectHeadings :: Pandoc -> [(Int, T.Text, String)]
collectHeadings (Pandoc _ blocks) = concatMap go blocks
  where
    go (Header lvl (ident, _, _) inlines)
        | lvl == 2 || lvl == 3
        = [(lvl, ident, T.unpack (stringify inlines))]
    go _ = []

-- ---------------------------------------------------------------------------
-- TOC tree
-- ---------------------------------------------------------------------------

data TOCNode = TOCNode T.Text String [TOCNode]

buildTree :: [(Int, T.Text, String)] -> [TOCNode]
buildTree = go 2
  where
    go _ [] = []
    go lvl ((l, i, t) : rest)
        | l == lvl  =
            let (childItems, remaining) = span (\(l', _, _) -> l' > lvl) rest
                children                = go (lvl + 1) childItems
            in  TOCNode i t children : go lvl remaining
        | l < lvl   = []
        | otherwise = go lvl rest   -- skip unexpected deeper items at this level

renderTOC :: [TOCNode] -> String
renderTOC [] = ""
renderTOC nodes = "<ol>\n" ++ concatMap renderNode nodes ++ "</ol>\n"
  where
    renderNode (TOCNode i t children) =
        "<li><a href=\"#" ++ T.unpack i ++ "\" data-target=\"" ++ T.unpack i ++ "\">"
        ++ Utils.escapeHtml t ++ "</a>" ++ renderTOC children ++ "</li>\n"

-- | Build a TOC HTML string from a Pandoc document.
buildTOC :: Pandoc -> String
buildTOC doc = renderTOC (buildTree (collectHeadings doc))

-- ---------------------------------------------------------------------------
-- Compilers
-- ---------------------------------------------------------------------------

-- | Register the bibliography inputs a citeproc run reads as tracked
--   Hakyll dependencies: the page's own @.bib@ file and every CSL style
--   under @data\/@.
--
--   Both are read through 'unsafeCompiler' (and, for the CSL, from a path
--   hard-coded in "Citations"), so nothing else puts them in the
--   dependency graph. Only files some rule actually claims can be
--   'load'ed — an identifier outside Hakyll's universe is a hard error,
--   and can never be out of date either — hence the 'getMatches' guard
--   and the matching no-route rules in "Site".
--
--   Scope note: the dependency is registered whether or not the page ends
--   up citing anything, because that is only known after citeproc has
--   run. The cost is recompiling non-citing pages when a @.bib@ changes;
--   the alternative is a page whose bibliography silently rots.
trackBibliographyInputs :: Identifier -> Compiler ()
trackBibliographyInputs bibIdent = do
    track (fromList [bibIdent])
    track ("data/*.csl" .&&. hasNoVersion)
  where
    track pat = do
        ids <- getMatches pat
        forM_ ids $ \i -> void (load i :: Compiler (Item String))

-- | Shared compiler pipeline parameterised on reader options.
--   Saves toc/word-count/reading-time/bibliography snapshots.
essayCompilerWith :: ReaderOptions -> Compiler (Item String)
essayCompilerWith rOpts = do
    -- Raw Markdown source (used for word count / reading time).
    body <- getResourceBody
    let src = itemBody body

    -- Apply source-level preprocessors (wikilinks, etc.) before parsing.
    let body' = itemSetBody (preprocessSource src) body

    -- Parse to Pandoc AST.
    --
    -- Heading levels are normalised immediately after parsing, before
    -- anything reads or emits a heading: the imported research essays use
    -- h1 for their body sections (the page title is an h1 from the
    -- template), which left the document with a dozen top-level headings
    -- and their major sections out of the TOC entirely, since
    -- 'collectHeadings' collects h2/h3. 'Filters.Headings.normalizeLevels'
    -- is the identity for every document that already starts at h2.
    rawPandoc  <- readPandocWith rOpts body'
    let pandocItem = fmap Headings.normalizeLevels rawPandoc

    -- Get further-reading keys from Hakyll metadata (YAML frontmatter is stripped
    -- before being passed to readPandocWith, so we read it from Hakyll instead).
    ident <- getUnderlying
    meta  <- getMetadata ident
    let frKeys = map T.pack $ fromMaybe [] (lookupStringList "further-reading" meta)
    let bibPath = T.pack $ fromMaybe "data/bibliography.bib" (lookupString "bibliography" meta)

    -- Bibliography inputs are read by citeproc inside 'unsafeCompiler',
    -- which is invisible to Hakyll's dependency graph: without an explicit
    -- 'load' an edit to a .bib entry (or to the CSL style) leaves every
    -- already-compiled page serving its cached bibliography. Loading the
    -- entry's own .bib and the CSL registers both as tracked inputs.
    -- Guarded by 'getMatches' because 'load' on an identifier no rule
    -- claims is a hard error, and 'bibliography:' is author-supplied.
    -- The synthetic /bibliography/ pages do the same over every .bib file
    -- (see build/Site.hs).
    trackBibliographyInputs (fromFilePath (T.unpack bibPath))

    -- Run citeproc, transform citation spans → superscripts, extract bibliography.
    (pandocWithCites, bibHtml, furtherHtml) <- unsafeCompiler $
        Citations.applyCitations frKeys bibPath (itemBody pandocItem)

    -- Inline SVG score fragments and data visualizations (both read files
    -- relative to the source file's directory).
    filePath <- getResourceFilePath
    let srcDir = takeDirectory filePath
    pandocWithScores <- unsafeCompiler $
        Score.inlineScores srcDir pandocWithCites
    pandocWithViz <- unsafeCompiler $
        Viz.inlineViz srcDir pandocWithScores

    -- Apply remaining AST-level filters (sidenotes, smallcaps, links, etc.).
    -- applyAll touches the filesystem via Images.apply (webp existence
    -- check), so it runs through unsafeCompiler.
    -- Opt-in figure numbering. Off unless the page asks for it: three
    -- essays already number by hand in three different conventions, and
    -- numbering them automatically would double up.
    let numberFigures =
            fromMaybe False (lookupString "figure-numbering" meta >>= parseBool)

    pandocFiltered <- unsafeCompiler $ applyAll numberFigures srcDir pandocWithViz
    let pandocItem'    = itemSetBody pandocFiltered pandocItem

    -- Build TOC from the filtered AST.
    let toc = buildTOC pandocFiltered

    -- Write HTML.
    let htmlItem = writePandocWith writerOpts pandocItem'

    -- Save snapshots keyed to this item's identifier.
    _ <- saveSnapshot "toc"                  (itemSetBody toc                            htmlItem)
    _ <- saveSnapshot "word-count"           (itemSetBody (show (wordCount src))         htmlItem)
    _ <- saveSnapshot "reading-time"         (itemSetBody (show (readingTime src))       htmlItem)
    _ <- saveSnapshot "bibliography"         (itemSetBody (T.unpack bibHtml)             htmlItem)
    _ <- saveSnapshot "further-reading-refs" (itemSetBody (T.unpack furtherHtml)         htmlItem)

    return htmlItem

-- | Compiler for essays.
essayCompiler :: Compiler (Item String)
essayCompiler = essayCompilerWith readerOpts

-- | Compiler for blog posts: same pipeline as essays.
postCompiler :: Compiler (Item String)
postCompiler = essayCompiler

-- | Compiler for poetry: enables hard_line_breaks so each source line becomes
--   a <br>, preserving verse line endings without manual trailing-space markup.
poetryCompiler :: Compiler (Item String)
poetryCompiler = essayCompilerWith poetryReaderOpts

-- | Compiler for fiction: same pipeline as essays; visual differences are
--   handled entirely by the reading template and reading.css.
fictionCompiler :: Compiler (Item String)
fictionCompiler = essayCompiler

-- | Compiler for music composition landing pages: full essay pipeline
--   (TOC, sidenotes, score fragments, citations, smallcaps, etc.).
compositionCompiler :: Compiler (Item String)
compositionCompiler = essayCompiler

-- | Compiler for photography pages: body prose runs through the same
--   source preprocessors and AST filters as other content (so wikilinks,
--   smallcaps, sidenotes, image @<picture>@ wrapping, etc. all work in
--   caption / process-note prose), but skips TOC, word-count,
--   reading-time, citations, and further-reading. Visual content has no
--   meaningful word count, and the epistemic / bibliography surfaces in
--   'essayCtx' don't apply here.
photographyCompiler :: Compiler (Item String)
photographyCompiler = do
    body <- getResourceBody
    let src   = itemBody body
        body' = itemSetBody (preprocessSource src) body
    filePath   <- getResourceFilePath
    let srcDir  = takeDirectory filePath
    pandocItem <- readPandocWith readerOpts body'
    pandocFiltered <- unsafeCompiler $ applyAll False srcDir (itemBody pandocItem)
    let pandocItem' = itemSetBody pandocFiltered pandocItem
    return (writePandocWith writerOpts pandocItem')

-- | Reduced pipeline for tag-meta sidecar markdown files. Applies
--   source-level preprocessors and AST filters (wikilinks, sidenotes,
--   smallcaps, links, etc.) so sidecar prose can use the same rich
--   markdown features as essays, then saves the rendered HTML under
--   the @"body"@ snapshot. Skips TOC, word count, reading time, and
--   citations — none of those belong in a portal intro. The item
--   itself is not routed; the body is consumed only via snapshot
--   loads by the tag-index rule and the home-page grid.
sidecarCompiler :: Compiler (Item String)
sidecarCompiler = do
    body <- getResourceBody
    let src   = itemBody body
        body' = itemSetBody (preprocessSource src) body
    filePath   <- getResourceFilePath
    let srcDir  = takeDirectory filePath
    pandocItem <- readPandocWith readerOpts body'
    pandocFiltered <- unsafeCompiler $ applyAll False srcDir (itemBody pandocItem)
    let pandocItem' = itemSetBody pandocFiltered pandocItem
    let htmlItem    = writePandocWith writerOpts pandocItem'
    _ <- saveSnapshot "body" htmlItem
    return htmlItem

-- | Compiler for simple pages: filters applied, no TOC snapshot.
pageCompiler :: Compiler (Item String)
pageCompiler = do
    body <- getResourceBody
    let src   = itemBody body
        body' = itemSetBody (preprocessSource src) body
    filePath   <- getResourceFilePath
    let srcDir  = takeDirectory filePath
    pandocItem <- readPandocWith readerOpts body'
    pandocFiltered <- unsafeCompiler $ applyAll False srcDir (itemBody pandocItem)
    let pandocItem' = itemSetBody pandocFiltered pandocItem
    let htmlItem    = writePandocWith writerOpts pandocItem'
    _ <- saveSnapshot "word-count"   (itemSetBody (show (wordCount src))   htmlItem)
    _ <- saveSnapshot "reading-time" (itemSetBody (show (readingTime src)) htmlItem)
    return htmlItem

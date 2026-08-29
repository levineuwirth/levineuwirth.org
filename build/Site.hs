{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
module Site (rules) where

import Control.Monad (forM, forM_, when)
import Data.Char     (isSpace, toUpper)
import Data.List     (groupBy, isPrefixOf, sort, sortBy, stripPrefix)
import Data.Map.Strict (Map)
import Data.Maybe    (catMaybes, fromMaybe, listToMaybe)
import Data.Ord      (Down (..), comparing)
import Data.Set      (Set)
import qualified Data.Set as Set
import qualified Data.Text as T
import System.Directory (listDirectory)
import System.Environment (lookupEnv)
import System.FilePath (takeDirectory, takeFileName, takeExtension, replaceExtension, (</>))
import Text.Read     (readMaybe)
import qualified Data.Aeson as Aeson
import qualified Data.ByteString.Lazy.Char8 as LBS
import qualified Data.Map.Strict as Map
import Hakyll
import Archive    (archiveRules)
import Authors    (buildAllAuthors, applyAuthorRules)
import Backlinks  (backlinkRules)
import BibExtras  (BibExtra (..), emptyBibExtra, firstAuthorSurname, parseBibExtras)
import Citations  (renderBibliographyHtml)
import Compilers  (essayCompiler, postCompiler, pageCompiler, poetryCompiler, fictionCompiler,
                   compositionCompiler, sidecarCompiler)
import Catalog      (musicCatalogCtx)
import Commonplace  (commonplaceCtx)
import Now          (nowCtx)
import Vita         (vitaCtx, projectsCtx)
import Contexts   (siteCtx, essayCtx, postCtx, pageCtx, poetryCtx, fictionCtx, compositionCtx,
                   contentKindField, declaresScore, recentFirstByDisplay,
                   tagLinksFieldExcludingTopSegment, isProvedConfidence)
import qualified Patterns as P
import Photography (photographyRules)
import Tags       (buildAllTags, applyTagRules, sidecarIdentifier,
                   portalIntroField, portalTooltipField)
import Pagination (blogPaginateRules)
import Stats      (statsRules)

-- | Home-page portal grid order. Canonical ordering authority for every
-- rendering of the portals (currently: the home page; future
-- consumers follow this list). Each entry is (display name, tag name);
-- the tag name is the key to everything else — URL (@/\<tag\>/@),
-- sidecar path (@content\/tag-meta\/\<tag\>.md@), and the Tags.hs
-- machinery that already keys off it. Edit this list to change order;
-- do not introduce an @order:@ frontmatter field on sidecars.
homePortals :: [(String, String)]
homePortals =
    [ ("Research",    "research")
    , ("Nonfiction",  "nonfiction")
    , ("Fiction",     "fiction")
    , ("Poetry",      "poetry")
    , ("Music",       "music")
    , ("Photography", "photography")
    , ("AI",          "ai")
    , ("Tech",        "tech")
    , ("Miscellany",  "miscellany")
    ]

-- | Default number of cards shown per library shelf. The sidecar
--   'featured:' list may push this up to 'libraryShelfMax'.
libraryShelfCap :: Int
libraryShelfCap = 4

-- | Hard ceiling on cards per shelf, regardless of sidecar length.
libraryShelfMax :: Int
libraryShelfMax = 5

-- | Optional prose intro lifted into @$library-intro$@ on the library
--   page. Matched but not routed; consumed via the @"body"@ snapshot.
libraryIntroId :: Identifier
libraryIntroId = fromFilePath "content/library.md"

-- | Route that strips a literal prefix from the identifier's path.
--   Hakyll's 'gsubRoute' replaces /every/ occurrence of its pattern, so
--   @gsubRoute "content/"@ would also mangle a co-located directory that
--   happened to be named @content@ deeper in the path
--   (@content/essays/slug/content/data.csv@ → @essays/slug/data.csv@).
--   This touches only the leading occurrence; identifiers that don't
--   start with the prefix pass through unchanged.
stripPrefixRoute :: String -> Routes
stripPrefixRoute prefix = customRoute $ \ident ->
    let fp = toFilePath ident
    in  fromMaybe fp (stripPrefix prefix fp)

feedConfig :: FeedConfiguration
feedConfig = FeedConfiguration
    { feedTitle       = "Levi Neuwirth"
    , feedDescription = "Essays, notes, and creative work by Levi Neuwirth"
    , feedAuthorName  = "Levi Neuwirth"
    , feedAuthorEmail = "levi@levineuwirth.org"
    , feedRoot        = "https://levineuwirth.org"
    }

musicFeedConfig :: FeedConfiguration
musicFeedConfig = FeedConfiguration
    { feedTitle       = "Levi Neuwirth — Music"
    , feedDescription = "New compositions by Levi Neuwirth"
    , feedAuthorName  = "Levi Neuwirth"
    , feedAuthorEmail = "levi@levineuwirth.org"
    , feedRoot        = "https://levineuwirth.org"
    }

-- | Context for the home page. Extends 'pageCtx' with a @portals@
-- listField iterating 'homePortals' in order. Each item exposes
-- @$portal-name$@, @$portal-url$@, and (if the sidecar's tooltip is
-- populated) @$portal-tooltip$@, consumed by @templates/home.html@.
-- Tooltip lookup uses 'portalTooltipField' — the same function
-- 'Tags.applyTagRules' uses on per-tag pages — so the two surfaces
-- stay in lockstep on suppression and missing-file semantics.
homeCtx :: Context String
homeCtx = listField "portals" portalItemCtx portalItems <> pageCtx
  where
    portalItems :: Compiler [Item (String, String)]
    portalItems = return (map (Item (fromFilePath "")) homePortals)

    portalItemCtx :: Context (String, String)
    portalItemCtx =
           field "portal-name" (return . fst . itemBody)
        <> field "portal-url"  (\i -> return $ "/" ++ snd (itemBody i) ++ "/")
        <> portalTooltipField (sidecarIdentifier . snd . itemBody)

rules :: Rules ()
rules = do
    -- ---------------------------------------------------------------------------
    -- Build mode. SITE_ENV=dev (set by `make dev` / `make watch`) includes
    -- drafts under content/drafts/**; anything else (unset, "deploy", "build")
    -- excludes them entirely from every match, listing, and asset rule below.
    -- ---------------------------------------------------------------------------
    isDev <- preprocess $ (== Just "dev") <$> lookupEnv "SITE_ENV"
    let allEssays = if isDev
                    then P.essayPattern .||. P.draftEssayPattern
                    else P.essayPattern

    -- ---------------------------------------------------------------------------
    -- Backlinks (pass 1: link extraction; pass 2: JSON generation)
    -- Must run before content rules so dependencies resolve correctly.
    -- ---------------------------------------------------------------------------
    backlinkRules

    -- ---------------------------------------------------------------------------
    -- Author index pages
    -- ---------------------------------------------------------------------------
    authors <- buildAllAuthors
    applyAuthorRules authors siteCtx

    -- ---------------------------------------------------------------------------
    -- Tag-meta sidecars — optional prose intros + tooltips for tag index
    -- pages and the home-page portal grid. Matched but not routed: the
    -- rendered body is exposed only via the @"body"@ snapshot and the
    -- @tooltip:@ frontmatter key is read through 'getMetadata' by the
    -- consumers (Tags.hs, home-page rule). Registered before tag rules so
    -- snapshot loads during tag-page compilation find a compiled target.
    --
    -- Two-pattern union: Hakyll's @**/*@ glob requires at least one
    -- subdirectory level, so flat sidecars (@content/tag-meta/nonfiction.md@)
    -- and nested sidecars (@content/tag-meta/nonfiction/philosophy.md@) must
    -- each be named by their own level-specific pattern.
    -- ---------------------------------------------------------------------------
    match ("content/tag-meta/*.md" .||. "content/tag-meta/**/*.md") $
        compile sidecarCompiler

    -- ---------------------------------------------------------------------------
    -- Tag index pages
    -- ---------------------------------------------------------------------------
    tags <- buildAllTags
    applyTagRules tags homePortals siteCtx
    statsRules tags

    -- Per-page JS files — authored alongside content in content/**/*.js.
    -- Draft JS is handled by a separate dev-only rule below.
    match ("content/**/*.js" .&&. complement "content/drafts/**") $ do
        route   $ stripPrefixRoute "content/"
        compile copyFileCompiler

    -- Per-page JS co-located with draft essays (dev-only).
    when isDev $ match "content/drafts/**/*.js" $ do
        route   $ stripPrefixRoute "content/"
        compile copyFileCompiler

    -- CSS — must be matched before the broad static/** rule to avoid
    -- double-matching (compressCssCompiler vs. copyFileCompiler).
    match "static/css/*" $ do
        route   $ stripPrefixRoute "static/"
        compile compressCssCompiler

    -- All other static files (fonts, JS, images, …). Build-time
    -- sidecars produced by the Python tooling (.dims.yaml, .exif.yaml,
    -- .palette.yaml) are excluded — they're consumed by Hakyll at
    -- compile time and have no role in the deployed site.
    match (   "static/**"
        .&&. complement "static/css/*"
        .&&. complement "static/**/*.dims.yaml"
        .&&. complement "static/**/*.exif.yaml"
        .&&. complement "static/**/*.palette.yaml"
        ) $ do
        route   $ stripPrefixRoute "static/"
        compile copyFileCompiler

    -- Templates
    match "templates/**" $ compile templateBodyCompiler

    -- ---------------------------------------------------------------------------
    -- Source-preview corpus — raw copies of source files, served at
    -- @/source/<path>@, fetched on hover by the popup provider in
    -- @static/js/popups.js@ (sourceContent → Prism highlighting).
    --
    -- Conservative whitelist: must stay aligned with 'isSourcePath' in
    -- @build/Filters/SourceRefs.hs@ so that every link the filter
    -- emits has a corresponding @/source/…@ target. Files in @static/@
    -- are also served under their normal /js/, /css/ paths via a
    -- separate rule above; the @"source-preview"@ version lets Hakyll
    -- compile the same identifier twice without conflict.
    --
    -- Anything not matched here will silently 404 on hover and the
    -- popup will simply not appear, which is the right failure mode
    -- if the heuristic ever wraps a path we did not mean to expose.
    -- ---------------------------------------------------------------------------
    let sourcePreviewable =
                 "build/**.hs"
            .||. "static/js/**"
            .||. "static/css/**"
            .||. "templates/**"
            .||. "tools/**.sh"
            .||. "tools/**.py"
            .||. "nginx/**.conf"
            .||. "data/*.json"
            .||. "data/*.yaml"
            .||. "data/*.md"
            .||. "data/*.bib"
            .||. "*.cabal"
            .||. "cabal.project"
            .||. "cabal.project.freeze"
            .||. "Makefile"
            .||. "pyproject.toml"
            .||. "uv.lock"
            .||. "LICENSE"
            .||. "checklist.md"
            .||. "WRITING.md"
            .||. "HOMEPAGE.md"
            .||. "PHOTOGRAPHY.md"
            .||. "README.md"
    match sourcePreviewable $ version "source-preview" $ do
        route   $ customRoute (\ident -> "source/" ++ toFilePath ident)
        compile copyFileCompiler

    -- Link annotations — author-defined previews for any URL
    match "data/annotations.json" $ do
        route   idRoute
        compile copyFileCompiler

    -- Semantic search index — produced by tools/embed.py; fetched at runtime
    -- by static/js/semantic-search.js from /data/semantic-index.bin and
    -- /data/semantic-meta.json.
    match ("data/semantic-index.bin" .||. "data/semantic-meta.json") $ do
        route   idRoute
        compile copyFileCompiler

    -- Similar links — produced by tools/embed.py; absent on first build or
    -- when .venv is not set up.  Compiled as a raw string for similarLinksField.
    match "data/similar-links.json" $ compile getResourceBody

    -- Commonplace YAML — compiled as a raw string so it can be loaded
    -- with dependency tracking by the commonplace page compiler.
    match "data/commonplace.yaml" $ compile getResourceBody

    -- Now YAML — same pattern as commonplace. Loaded by Now.nowCtx for
    -- /current.html. Re-compiles current.html when the YAML changes.
    match "data/now.yaml" $ compile getResourceBody

    -- CV/résumé YAML — the same files the PDF pipeline builds from
    -- (yaml-source/data/). Loaded by Vita.vitaCtx so /about.html renders
    -- education, publications, presentations, and experience from one
    -- source instead of a hand-typed copy. Matching them here is what
    -- makes about.html recompile when the CV data changes.
    match "yaml-source/data/*.yml" $ compile getResourceBody

    -- Per-build stamp — written by Main.main before Hakyll starts, so it
    -- always exists and always differs from the previous run. Matched
    -- (not routed) purely so the telemetry pages can `load` it as a
    -- dependency and thus recompile every build instead of serving a
    -- stale cached copy. See build/Stats.hs.
    match "data/build-stamp.txt" $ compile getResourceBody

    -- ---------------------------------------------------------------------------
    -- Homepage
    -- ---------------------------------------------------------------------------
    match "content/index.md" $ do
        route   $ constRoute "index.html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/home.html"    homeCtx
            >>= loadAndApplyTemplate "templates/default.html" homeCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Standalone pages (me/, colophon.md, …)
    -- ---------------------------------------------------------------------------
    -- me/index.md — compiled as a full essay (TOC, metadata block, sidenotes).
    -- Lives in its own directory so co-located SVG score fragments resolve
    -- correctly: the Score filter reads paths relative to the source file's
    -- directory (content/me/), not the content root.
    match "content/me/index.md" $ do
        route   $ constRoute "me.html"
        compile $ essayCompiler
            >>= loadAndApplyTemplate "templates/essay.html"   essayCtx
            >>= loadAndApplyTemplate "templates/default.html" essayCtx
            >>= relativizeUrls

    -- SVG score fragments co-located with me/index.md.
    match "content/me/scores/*.svg" $ do
        route   $ stripPrefixRoute "content/me/"
        compile copyFileCompiler

    -- memento-mori/index.md — lives in its own directory so co-located SVG
    -- score fragments resolve correctly (same pattern as me/index.md).
    match "content/memento-mori/index.md" $ do
        route   $ constRoute "memento-mori.html"
        compile $ essayCompiler
            >>= loadAndApplyTemplate "templates/essay.html"
                    (constField "memento-mori" "true" <> essayCtx)
            >>= loadAndApplyTemplate "templates/default.html"
                    (constField "memento-mori" "true" <> essayCtx)
            >>= relativizeUrls

    -- SVG score fragments co-located with memento-mori/index.md.
    match "content/memento-mori/scores/*.svg" $ do
        route   $ stripPrefixRoute "content/memento-mori/"
        compile copyFileCompiler

    -- ---------------------------------------------------------------------------
    -- Commonplace book
    -- ---------------------------------------------------------------------------
    match "content/commonplace.md" $ do
        route   $ constRoute "commonplace.html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/commonplace.html" commonplaceCtx
            >>= loadAndApplyTemplate "templates/default.html"     commonplaceCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Now — research-first status page driven by data/now.yaml. Same
    -- structural pattern as the commonplace page: markdown body
    -- (optional intro prose) + structured YAML rendered into HTML by
    -- Now.nowCtx, then assembled by templates/current.html.
    -- ---------------------------------------------------------------------------
    match "content/current.md" $ do
        route   $ constRoute "current.html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/current.html" nowCtx
            >>= loadAndApplyTemplate "templates/default.html" nowCtx
            >>= relativizeUrls

    match "content/colophon.md" $ do
        route   $ constRoute "colophon.html"
        compile $ essayCompiler
            >>= loadAndApplyTemplate "templates/essay.html"   essayCtx
            >>= loadAndApplyTemplate "templates/default.html" essayCtx
            >>= relativizeUrls

    -- Vita — the academic-homepage view, driven by yaml-source/data/*.yml.
    -- Prose (research interests, pointers, contact) stays in the markdown
    -- body; education, publications, presentations, and experience are
    -- generated by Vita.vitaCtx and assembled by templates/vita.html.
    match "content/about.md" $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/vita.html"    vitaCtx
            >>= loadAndApplyTemplate "templates/default.html" vitaCtx
            >>= relativizeUrls

    match ("content/*.md"
            .&&. complement "content/index.md"
            .&&. complement "content/about.md"
            .&&. complement "content/commonplace.md"
            .&&. complement "content/colophon.md"
            .&&. complement "content/current.md"
            .&&. complement "content/library.md") $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/page.html"    pageCtx
            >>= loadAndApplyTemplate "templates/default.html" pageCtx
            >>= relativizeUrls

    -- Generic page collections
    -- (content/<collection>/<slug>.md → <collection>/<slug>.html).
    match P.pageCollectionPattern $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/page.html"    pageCtx
            >>= loadAndApplyTemplate "templates/default.html" pageCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- CV routing pages (content/cv/*.md → /cv/<slug>/).
    -- These are narrative overlays pointing into the library; they render
    -- with the same page.html pipeline as top-level standalone pages, but
    -- route to directory-style URLs (/cv/projects/ rather than /cv/projects.html)
    -- so nginx serves them via index-file resolution and the URLs stay stable
    -- if the underlying files are later reorganized into co-located directories.
    -- ---------------------------------------------------------------------------
    -- The project index is generated from yaml-source/data/projects.yml —
    -- the same file that feeds the CV's and résumé's project sections — so
    -- it gets projectsCtx and its own template. The markdown keeps only the
    -- page's framing prose. Individual project writeups stay as essays.
    match "content/cv/projects.md" $ do
        route $ constRoute "cv/projects/index.html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/projects.html" projectsCtx
            >>= loadAndApplyTemplate "templates/default.html"  projectsCtx
            >>= relativizeUrls

    match ("content/cv/*.md" .&&. complement "content/cv/projects.md") $ do
        route $ customRoute $ \ident ->
            let fname = takeFileName (toFilePath ident)
                slug  = takeWhile (/= '.') fname
            in "cv/" ++ slug ++ "/index.html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/page.html"    pageCtx
            >>= loadAndApplyTemplate "templates/default.html" pageCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Essays — flat (content/essays/foo.md → essays/foo.html) and
    --          directory-based (content/essays/slug/index.md → essays/slug/index.html).
    --          In dev mode, drafts under content/drafts/essays/ route to
    --          drafts/essays/foo.html (flat) or drafts/essays/slug/index.html (dir).
    -- ---------------------------------------------------------------------------
    match allEssays $ do
        route $ customRoute $ \ident ->
            let fp           = toFilePath ident
                fname        = takeFileName fp
                isIndex      = fname == "index.md"
                isDraft      = "content/drafts/essays/" `isPrefixOf` fp
                stripContent = fromMaybe fp (stripPrefix "content/" fp)
                isNested     = takeDirectory fp /= "content/essays"
            in case (isDraft, isIndex) of
                -- content/drafts/essays/slug/index.md → drafts/essays/slug/index.html
                (True,  True)  -> replaceExtension stripContent "html"
                -- content/drafts/essays/foo.md → drafts/essays/foo.html
                (True,  False) -> "drafts/essays/" ++ replaceExtension fname "html"
                -- Published directory essays and collection entries retain
                -- their directory path below content/.
                (False, _) | isNested -> replaceExtension stripContent "html"
                -- content/essays/foo.md → essays/foo.html
                (False, False) -> "essays/" ++ replaceExtension fname "html"
                (False, True)  -> replaceExtension stripContent "html"
        compile $ essayCompiler
            >>= saveSnapshot "content"
            >>= loadAndApplyTemplate "templates/essay.html"   essayCtx
            >>= loadAndApplyTemplate "templates/default.html" essayCtx
            >>= relativizeUrls

    -- Static assets co-located with directory-based essays (figures, data, PDFs, …).
    -- Build-time dimension sidecars are excluded; they're consumed by
    -- Filters/Images.hs at compile time, not shipped.
    match ("content/essays/**"
           .&&. complement P.essayPattern
           .&&. complement "content/essays/**/*.dims.yaml") $ do
        route $ stripPrefixRoute "content/"
        compile copyFileCompiler

    -- Static assets co-located with draft essays (dev-only).
    when isDev $ match ("content/drafts/essays/**"
                        .&&. complement "content/drafts/essays/*.md"
                        .&&. complement "content/drafts/essays/*/index.md"
                        .&&. complement "content/drafts/essays/**/*.dims.yaml") $ do
        route $ stripPrefixRoute "content/"
        compile copyFileCompiler

    -- ---------------------------------------------------------------------------
    -- Blog posts
    -- ---------------------------------------------------------------------------
    match P.blogPattern $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ postCompiler
            >>= saveSnapshot "content"
            >>= loadAndApplyTemplate "templates/blog-post.html" postCtx
            >>= loadAndApplyTemplate "templates/default.html"   postCtx
            >>= relativizeUrls

    -- Blog collection index pages
    -- (content/blog/<collection>/index.md → blog/<collection>/index.html).
    match "content/blog/*/index.md" $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/default.html" pageCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Poetry
    -- ---------------------------------------------------------------------------
    -- All poems — flat (content/poetry/sonnet-60.md) and collection
    -- (content/poetry/shakespeare-sonnets/sonnet-1.md) forms share one
    -- rule; collection index pages are excluded by 'P.poetryPattern'
    -- itself and matched separately below.
    match P.poetryPattern $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ poetryCompiler
            >>= saveSnapshot "content"
            >>= loadAndApplyTemplate "templates/reading.html"  poetryCtx
            >>= loadAndApplyTemplate "templates/default.html"  poetryCtx
            >>= relativizeUrls

    -- Collection index pages (e.g. content/poetry/shakespeare-sonnets/index.md)
    match "content/poetry/*/index.md" $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/default.html"  pageCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Fiction
    -- ---------------------------------------------------------------------------
    match P.fictionPattern $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ fictionCompiler
            >>= saveSnapshot "content"
            >>= loadAndApplyTemplate "templates/reading.html"  fictionCtx
            >>= loadAndApplyTemplate "templates/default.html"  fictionCtx
            >>= relativizeUrls

    -- Fiction collection index pages
    -- (content/fiction/<collection>/index.md → fiction/<collection>/index.html).
    match "content/fiction/*/index.md" $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/default.html" pageCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Music — catalog index
    -- ---------------------------------------------------------------------------
    match "content/music/index.md" $ do
        route   $ constRoute "music/index.html"
        compile $ pageCompiler
            >>= loadAndApplyTemplate "templates/music-catalog.html" musicCatalogCtx
            >>= loadAndApplyTemplate "templates/default.html"       musicCatalogCtx
            >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Music — composition landing pages + score reader
    -- ---------------------------------------------------------------------------

    -- Static assets (SVG score pages, audio, PDF) served unchanged.
    match "content/music/**/*.svg" $ do
        route   $ stripPrefixRoute "content/"
        compile copyFileCompiler

    match "content/music/**/*.mp3" $ do
        route   $ stripPrefixRoute "content/"
        compile copyFileCompiler

    match "content/music/**/*.pdf" $ do
        route   $ stripPrefixRoute "content/"
        compile copyFileCompiler

    -- Landing page — full essay pipeline.
    match "content/music/*/index.md" $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ compositionCompiler
            >>= saveSnapshot "content"
            >>= loadAndApplyTemplate "templates/composition.html"  compositionCtx
            >>= loadAndApplyTemplate "templates/default.html"      compositionCtx
            >>= relativizeUrls

    -- Score reader — separate URL, minimal chrome.
    -- Compiled from the same source with version "score-reader".
    --
    -- Gated on the composition declaring a score. Ungated, every
    -- composition got a live /music/<slug>/score/ whose reader had nothing
    -- to show: an empty <img>, a "p. 1 / 0" counter, and an enabled Next
    -- button. 'declaresScore' is metadata-only because 'matchMetadata'
    -- runs before the Compiler monad exists — a 'score-dir' naming an
    -- empty directory still routes a page, which 'scorePageList' then
    -- reports honestly as zero pages.
    matchMetadata "content/music/*/index.md" declaresScore $
        version "score-reader" $ do
            route $ customRoute $ \ident ->
                let slug = takeFileName . takeDirectory . toFilePath $ ident
                in  "music/" ++ slug ++ "/score/index.html"
            compile $ do
                makeItem ""
                    >>= loadAndApplyTemplate "templates/score-reader.html"
                                             compositionCtx
                    >>= loadAndApplyTemplate "templates/score-reader-default.html"
                                             compositionCtx
                    >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Photography — single-photo entries, asset copy, and section landing.
    -- See build/Photography.hs and PHOTOGRAPHY.md for the design.
    -- ---------------------------------------------------------------------------
    photographyRules

    -- ---------------------------------------------------------------------------
    -- Archive — link-archiving system: per-entry /archive/<slug>/ pages and
    -- the /archive/ index, driven by archive/manifest.yaml + PROVENANCE.json.
    -- See build/Archive.hs and ARCHIVE.md for the design.
    -- ---------------------------------------------------------------------------
    archiveRules

    -- ---------------------------------------------------------------------------
    -- Blog index (paginated)
    -- ---------------------------------------------------------------------------
    blogPaginateRules postCtx siteCtx

    -- ---------------------------------------------------------------------------
    -- Essay index
    -- ---------------------------------------------------------------------------
    create ["essays/index.html"] $ do
        route idRoute
        compile $ do
            essays <- recentFirst =<< loadAll (allEssays .&&. hasNoVersion)
            let ctx =
                    listField "essays" essayCtx (return essays)
                    <> constField "title"  "Essays"
                    <> constField "portal" "true"
                    <> siteCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/essay-index.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"      ctx
                >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Poetry index
    -- ---------------------------------------------------------------------------
    -- Nav, the home portal grid, and the library all link /poetry/; this
    -- rule is what keeps those links from 404ing. Lists flat poems and
    -- collection poems alike; collection index pages are excluded by
    -- 'P.poetryPattern' itself.
    create ["poetry/index.html"] $ do
        route idRoute
        compile $ do
            poems <- recentFirst =<< loadAll (P.poetryPattern .&&. hasNoVersion)
            let ctx =
                    listField "essays" poetryCtx (return poems)
                    <> constField "title"  "Poetry"
                    <> constField "portal" "true"
                    <> siteCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/essay-index.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"      ctx
                >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Fiction index
    -- ---------------------------------------------------------------------------
    -- Same rationale as the poetry index. content/fiction/ has no entries
    -- yet; an empty match list renders an empty index rather than a 404.
    create ["fiction/index.html"] $ do
        route idRoute
        compile $ do
            stories <- recentFirst =<< loadAll (P.fictionPattern .&&. hasNoVersion)
            let ctx =
                    listField "essays" fictionCtx (return stories)
                    <> constField "title"  "Fiction"
                    <> constField "portal" "true"
                    <> siteCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/essay-index.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"      ctx
                >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- New page — all content sorted by creation date, newest first
    -- ---------------------------------------------------------------------------
    create ["new.html"] $ do
        route idRoute
        compile $ do
            let allContent = (   allEssays
                             .||. P.blogPattern
                             .||. P.fictionPattern
                             .||. P.poetryPattern
                             .||. P.musicPattern
                             ) .&&. hasNoVersion
            items <- recentFirstByDisplay =<< loadAll allContent
            let itemCtx = contentKindField
                       <> essayCtx
                ctx = listField "recent-items" itemCtx (return items)
                   <> constField "title" "New"
                   <> constField "list-page" "true"
                   <> siteCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/new.html"     ctx
                >>= loadAndApplyTemplate "templates/default.html" ctx
                >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Library intro — optional prose block (typically a blockquote) lifted
    -- into @$library-intro$@ at the top of /library.html. Matched but not
    -- routed; the body snapshot is consumed by the library rule below.
    -- ---------------------------------------------------------------------------
    match "content/library.md" $ compile sidecarCompiler

    -- ---------------------------------------------------------------------------
    -- Library — portal-grouped view over the /new.html dataset, deduplicated
    -- by primary portal. An item's primary portal is the top segment of the
    -- first tag in its frontmatter 'tags:' list whose top segment matches a
    -- known portal (those in 'homePortals'). Items with no such tag are
    -- silently dropped from the library (they remain on /new.html and on any
    -- tag pages their frontmatter produces).
    --
    -- Each shelf is capped at 'libraryShelfCap' items by default. A portal's
    -- tag-meta sidecar may carry a 'featured:' list of content-rooted paths
    -- (e.g. @content/essays/foo.md@); featured items are placed first, in
    -- listed order, and the remainder is filled by recency up to a hard
    -- ceiling of 'libraryShelfMax'. Featured paths that don't resolve to an
    -- item in the portal (wrong primary portal, or typo) are silently
    -- dropped. When the unfiltered portal has more items than the shelf
    -- shows, @$<slug>-has-more$@ is exposed so the template can render a
    -- "More on this shelf →" affordance linking to the portal's tag page.
    --
    -- Each card uses the shared item-card partial, with cross-portal filings
    -- rendered in the card's tag footer via 'tagLinksFieldExcludingTopSegment',
    -- scoped to the section's portal so the portal's own tag is suppressed.
    -- ---------------------------------------------------------------------------
    create ["library.html"] $ do
        route idRoute
        compile $ do
            sidecarIds <- getMatches ("content/tag-meta/*.md"
                                 .||. "content/tag-meta/**/*.md")
            let sidecarSet   = Set.fromList sidecarIds
                knownPortals = map snd homePortals

                -- Top segment of the first tag that names a known portal.
                -- Nothing when no tag matches — item is excluded from library.
                -- Reads tags via 'getTags' (not lookupStringList) so the
                -- scalar comma form ("tags: research, ai") is accepted with
                -- the same semantics the tag pages use.
                primaryPortalOf item = do
                    ts <- getTags (itemIdentifier item)
                    return $ listToMaybe
                        [ p | t <- ts
                            , let p = takeWhile (/= '/') t
                            , p `elem` knownPortals ]

                -- Per-section item context: kind badge, ISO date for datetime
                -- attr, human-readable display date via essayCtx's dateDisplayField,
                -- abstract via siteCtx's abstractField, and cross-portal filings
                -- in the footer. Suppression is top-segment-based (hide every
                -- tag under the section's portal, not just the exact match) so
                -- a Research-section card doesn't re-list its research/* filings
                -- alongside the section heading. @full-abstract@ unclamps the
                -- card's 2-line abstract truncation — Library is the canonical
                -- browsing surface and shows full abstracts.
                portalItemCtx p =
                    contentKindField
                    <> tagLinksFieldExcludingTopSegment "item-tags" p
                    <> constField "full-abstract" "true"
                    <> essayCtx

            -- Load every content item once, then partition by primary portal
            -- so each shelf draws from a pre-filtered list rather than
            -- re-scanning the whole corpus once per portal.
            essays  <- loadAll (allEssays            .&&. hasNoVersion)
            posts   <- loadAll (P.blogPattern        .&&. hasNoVersion)
            fiction <- loadAll (P.fictionPattern     .&&. hasNoVersion)
            poetry  <- loadAll (P.poetryPattern      .&&. hasNoVersion)
            music   <- loadAll (P.musicPattern       .&&. hasNoVersion)
            photos  <- loadAll (P.photographyPattern .&&. hasNoVersion)
            let allContent = essays ++ posts ++ fiction ++ poetry ++ music ++ photos
                                :: [Item String]
            tagged <- mapM (\i -> (,i) <$> primaryPortalOf i) allContent
            let itemsByPortal :: Map.Map String [Item String]
                itemsByPortal =
                    Map.fromListWith (++) [(p, [i]) | (Just p, i) <- tagged]

            -- Existence-guarded, like the sidecar contexts in Tags.hs:
            -- deleting content/library.md degrades to a library page with
            -- no intro block rather than failing the whole compile. When
            -- the file exists, the eager snapshot load registers the
            -- library-intro dependency unconditionally, so a first-populate
            -- of content/library.md re-renders the library page even when
            -- the gate was previously false (see 'sidecarContext' in
            -- Tags.hs for the same pattern).
            introIds <- getMatches "content/library.md"
            libraryIntroFld <-
                if libraryIntroId `elem` introIds
                    then do
                        _ <- loadSnapshot libraryIntroId "body" :: Compiler (Item String)
                        return $ field "library-intro" $ \_ -> do
                            html <- itemBody <$> loadSnapshot libraryIntroId "body"
                            if all isSpace html
                                then noResult "empty library intro"
                                else return html
                    else return mempty

            -- One shelf's context contribution: the @<slug>-entries@
            -- listField (or absent via noResult when the shelf is
            -- empty) plus an optional @<slug>-has-more@ gate.
            let portalSection p = do
                    let portalItems = fromMaybe [] (Map.lookup p itemsByPortal)
                    sorted <- recentFirstByDisplay portalItems

                    featuredPaths <-
                        if sidecarIdentifier p `Set.member` sidecarSet
                            then do
                                meta <- getMetadata (sidecarIdentifier p)
                                return (fromMaybe [] (lookupStringList "featured" meta))
                            else return []

                    let portalIdSet =
                            Set.fromList (map itemIdentifier portalItems)
                        featuredItems =
                            [ i
                            | path <- featuredPaths
                            , let ident = fromFilePath path
                            , ident `Set.member` portalIdSet
                            , Just i <- [listToMaybe
                                (filter ((== ident) . itemIdentifier) portalItems)]
                            ]
                        cap = min libraryShelfMax
                                  (max libraryShelfCap (length featuredItems))
                        featuredIds =
                            Set.fromList (map itemIdentifier featuredItems)
                        rest = filter (\i -> not (itemIdentifier i `Set.member` featuredIds)) sorted
                        merged = take cap (featuredItems ++ rest)

                    let entriesFld =
                            listField (p ++ "-entries") (portalItemCtx p)
                                (if null merged
                                    then noResult ("no items in portal " ++ p)
                                    else return merged)
                        hasMoreFld
                            | length portalItems > length merged =
                                constField (p ++ "-has-more") "true"
                            | otherwise = mempty

                    return (entriesFld <> hasMoreFld)

            -- Section order follows homePortals — single ordering authority.
            sections <- mapM portalSection knownPortals

            let ctx = mconcat sections
                   <> libraryIntroFld
                   <> constField "title"   "Library"
                   <> constField "library" "true"
                   <> constField "portal"  "true"
                   <> siteCtx

            makeItem ""
                >>= loadAndApplyTemplate "templates/library.html"  ctx
                >>= loadAndApplyTemplate "templates/default.html"  ctx
                >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Bibliography — synthetic index + per-keyword pages (Phase 6b).
    -- ---------------------------------------------------------------------------
    -- Bibliography-meta sidecars: same shape as tag-meta, used by the
    -- per-keyword pages for the prose intro and (future) tooltips. No
    -- route; body snapshot consumed by the keyword rule.
    match ("content/bibliography-meta/*.md" .||. "content/bibliography-meta/**/*.md") $
        compile sidecarCompiler

    -- Collect the universe of keywords at rule-gen time. Two sources:
    --   * @keywords:@ fields across all @data/*.bib@ entries
    --   * @keywords:@ frontmatter across all essays + blog + poetry +
    --     fiction + music-composition pages
    -- The union drives which @/bibliography/\<kw\>/@ pages get generated;
    -- keywords with no referents anywhere are not synthesized into pages.
    bibFilePaths <- preprocess $ do
        files <- listDirectory "data"
        return $ sort [ "data" </> f | f <- files, takeExtension f == ".bib" ]

    bibExtrasAll <- preprocess $
        Map.unions <$> mapM parseBibExtras bibFilePaths

    let bibKwMap :: Map String [String]
        bibKwMap = invertKeywordsBib bibExtrasAll

    writingIds <- getMatches $ (P.essayPattern
                            .||. P.blogPattern
                            .||. P.fictionPattern
                            .||. P.poetryPattern
                            .||. P.musicPattern)
                          .&&. hasNoVersion

    writingKwPairs <- forM writingIds $ \ident -> do
        meta <- getMetadata ident
        let kws = readKeywords meta
        return (ident, kws)

    let writingKwMap :: Map String [Identifier]
        writingKwMap = invertKeywordsWritings writingKwPairs

        -- Keywords with at least one referent (writing OR bib entry).
        allKeywords :: Set String
        allKeywords = Set.union (Map.keysSet bibKwMap) (Map.keysSet writingKwMap)

    -- Identifiers of bibliography-meta sidecars that exist on disk,
    -- used to optionally inject $portal-intro$ + $portal-tooltip$ on
    -- keyword pages when the author populates a sidecar.
    bibMetaIds <- getMatches ("content/bibliography-meta/*.md"
                         .||. "content/bibliography-meta/**/*.md")
    let bibMetaSet = Set.fromList bibMetaIds

    -- /bibliography/index.html — every entry across every .bib file.
    -- Sort: ascending by first-author surname, year-descending within
    -- author (scholarly convention).
    create ["bibliography/index.html"] $ do
        route idRoute
        compile $ do
            let sortedKeys = bibliographyIndexOrder bibExtrasAll
                grouped    = groupByLetter bibExtrasAll sortedKeys
                present    = map fst grouped
            html <- unsafeCompiler $ do
                parts <- forM grouped $ \(letter, keys) -> do
                    body <- renderBibliographyHtml bibFilePaths bibExtrasAll keys
                    return (renderLetterHeader letter <> body)
                return (renderBibliographyAlphabet present <> T.concat parts)
            let ctx = constField "title"          "Bibliography"
                   <> constField "bibliography-index" "true"
                   <> constField "bibliography-entries" (T.unpack html)
                   <> constField "library" "true"  -- reuse flag to load library.css + item-card.css
                   <> constField "portal"  "true"
                   <> siteCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/bibliography-index.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"            ctx
                >>= relativizeUrls

    -- /bibliography/<keyword>/index.html for each keyword in the union.
    forM_ (Set.toList allKeywords) $ \kw ->
        create [fromFilePath ("bibliography/" ++ kw ++ "/index.html")] $ do
            route idRoute
            compile $ do
                -- Writings section
                let wIds = fromMaybe [] (Map.lookup kw writingKwMap)
                writingItems <- case wIds of
                    [] -> return []
                    _  -> recentFirstByDisplay
                            =<< mapM (\i -> load i :: Compiler (Item String)) wIds
                let writingsCtx
                        | null writingItems = mempty
                        | otherwise = listField "writings" (portalWritingCtx kw)
                                        (return writingItems)
                                   <> constField "has-writings" "true"

                -- References section
                let refKeys = keywordReferencesOrder bibExtrasAll kw
                refsHtml <- unsafeCompiler $
                    renderBibliographyHtml bibFilePaths bibExtrasAll refKeys
                let referencesCtx
                        | null refKeys = mempty
                        | otherwise =
                            constField "references" (T.unpack refsHtml)

                -- Sidecar (tooltip + optional prose intro)
                let sidecarId = bibliographyMetaIdentifier kw
                    hasSidecar = sidecarId `Set.member` bibMetaSet
                scCtx <- if hasSidecar
                    then do
                        _ <- loadSnapshot sidecarId "body" :: Compiler (Item String)
                        return (portalIntroField   (const sidecarId)
                             <> portalTooltipField (const sidecarId))
                    else return mempty

                let ctx = constField "title"          kw
                       <> constField "keyword"        kw
                       <> constField "bibliography-keyword" "true"
                       <> constField "library" "true"  -- reuse flag to load library.css + item-card.css
                       <> writingsCtx
                       <> referencesCtx
                       <> scCtx
                       <> siteCtx
                makeItem ""
                    >>= loadAndApplyTemplate "templates/bibliography-keyword.html" ctx
                    >>= loadAndApplyTemplate "templates/default.html"              ctx
                    >>= relativizeUrls

    -- ---------------------------------------------------------------------------
    -- Random page manifest — essays, blog posts, fiction, and poetry (flat
    -- and collection poems alike). No pagination/index pages; music and
    -- photography landings are also excluded.
    -- ---------------------------------------------------------------------------
    create ["random-pages.json"] $ do
        route idRoute
        compile $ do
            essays  <- loadAll (allEssays        .&&. hasNoVersion) :: Compiler [Item String]
            posts   <- loadAll (P.blogPattern    .&&. hasNoVersion) :: Compiler [Item String]
            fiction <- loadAll (P.fictionPattern .&&. hasNoVersion) :: Compiler [Item String]
            poetry  <- loadAll (P.poetryPattern  .&&. hasNoVersion) :: Compiler [Item String]
            routes  <- mapM (getRoute . itemIdentifier) (essays ++ posts ++ fiction ++ poetry)
            let urls = [ "/" ++ r | Just r <- routes ]
            makeItem $ LBS.unpack (Aeson.encode urls)

    -- ---------------------------------------------------------------------------
    -- Epistemic metadata manifest — maps page URLs to epistemic fields
    -- (status, confidence, importance, evidence, scope, novelty, practicality,
    -- stability, score) for client-side search filtering.
    -- ---------------------------------------------------------------------------
    create ["data/epistemic-meta.json"] $ do
        route idRoute
        compile $ do
            essays  <- loadAll (allEssays        .&&. hasNoVersion) :: Compiler [Item String]
            posts   <- loadAll (P.blogPattern    .&&. hasNoVersion) :: Compiler [Item String]
            fiction <- loadAll (P.fictionPattern .&&. hasNoVersion) :: Compiler [Item String]
            poetry  <- loadAll (P.poetryPattern  .&&. hasNoVersion) :: Compiler [Item String]
            music   <- loadAll (P.musicPattern   .&&. hasNoVersion) :: Compiler [Item String]
            let items = essays ++ posts ++ fiction ++ poetry ++ music
            pairs <- mapM epistemicEntry items
            let metaMap = Map.fromList (catMaybes pairs)
            makeItem $ LBS.unpack (Aeson.encode metaMap)

    -- ---------------------------------------------------------------------------
    -- Atom feed — all content sorted by date
    -- ---------------------------------------------------------------------------
    create ["feed.xml"] $ do
        route idRoute
        compile $ do
            posts <- fmap (take 30) . recentFirst
                        =<< loadAllSnapshots
                                (   (    allEssays
                                    .||. P.blogPattern
                                    .||. P.fictionPattern
                                    .||. P.poetryPattern
                                    .||. P.musicPattern
                                    )
                                .&&. hasNoVersion
                                )
                                "content"
            let feedCtx =
                    dateField "updated"   "%Y-%m-%dT%H:%M:%SZ"
                    <> dateField "published" "%Y-%m-%dT%H:%M:%SZ"
                    <> bodyField "description"
                    <> defaultContext
            renderAtom feedConfig feedCtx posts

    -- ---------------------------------------------------------------------------
    -- Music feed — compositions only
    -- ---------------------------------------------------------------------------
    create ["music/feed.xml"] $ do
        route idRoute
        compile $ do
            compositions <- recentFirst
                        =<< loadAllSnapshots
                                (P.musicPattern .&&. hasNoVersion)
                                "content"
            let feedCtx =
                    dateField "updated"   "%Y-%m-%dT%H:%M:%SZ"
                    <> dateField "published" "%Y-%m-%dT%H:%M:%SZ"
                    <> bodyField "description"
                    <> defaultContext
            renderAtom musicFeedConfig feedCtx compositions

    -- ---------------------------------------------------------------------------
    -- robots.txt — minimal, just points crawlers at the sitemap
    -- ---------------------------------------------------------------------------
    create ["robots.txt"] $ do
        route idRoute
        compile $ makeItem $ unlines
            -- /archive/ is *deliberately not* disallowed. Crawlers must be
            -- able to reach the wrapper pages (and snapshot.html) to see
            -- their <meta name=robots content="noindex, noarchive">; a
            -- robots.txt Disallow would block that and a URL blocked only
            -- by robots.txt can still appear in results when linked. The
            -- raw PDFs cannot carry meta — they need an `X-Robots-Tag`
            -- HTTP header from the deploy webserver (see nginx/archive.conf).
            [ "User-agent: *"
            , "Allow: /"
            , ""
            , "Sitemap: https://levineuwirth.org/sitemap.xml"
            ]

    -- ---------------------------------------------------------------------------
    -- sitemap.xml — every dated content page (essays, blog, poetry, fiction,
    -- music). Standalone pages (about, colophon, etc.) are intentionally
    -- omitted: they're reachable via the main nav, lack `date:` frontmatter,
    -- and would force a fallback lastmod that misrepresents staleness.
    -- ---------------------------------------------------------------------------
    create ["sitemap.xml"] $ do
        route idRoute
        compile $ do
            entries <- recentFirst
                        =<< loadAllSnapshots
                                (   (    allEssays
                                    .||. P.blogPattern
                                    .||. P.fictionPattern
                                    .||. P.poetryPattern
                                    .||. P.musicPattern
                                    )
                                .&&. hasNoVersion
                                )
                                "content"
            let siteRoot = "https://levineuwirth.org"
                sitemapItemCtx =
                    constField "root" siteRoot
                    <> dateField "lastmod" "%Y-%m-%d"
                    <> defaultContext
                sitemapCtx =
                    constField "root" siteRoot
                    <> listField "entries" sitemapItemCtx (return entries)
            makeItem ("" :: String)
                >>= loadAndApplyTemplate "templates/sitemap.xml" sitemapCtx

-- ---------------------------------------------------------------------------
-- Epistemic metadata extraction
-- ---------------------------------------------------------------------------

-- | Extract epistemic metadata from a content item's frontmatter.
--   Returns Nothing if the item has no route or no epistemic fields.
epistemicEntry :: Item String -> Compiler (Maybe (String, Map.Map String String))
epistemicEntry item = do
    let ident = itemIdentifier item
    mRoute <- getRoute ident
    case mRoute of
        Nothing -> return Nothing
        Just r  -> do
            meta <- getMetadata ident
            let url = "/" ++ r
                fields = catMaybes
                    [ grab "status"       meta
                    , grab "confidence"   meta
                    , grab "importance"   meta
                    , grab "evidence"     meta
                    , grab "scope"        meta
                    , grab "novelty"      meta
                    , grab "practicality" meta
                    , grab "stability"    meta
                    ]
                obj = Map.fromList fields
                -- Compute overall-score the same way Contexts.overallScoreField
                -- does, including the "proved"/"proven" sentinel -> 100.
                confRaw = lookupString "confidence" meta
                confInt | isProvedConfidence confRaw = Just 100
                        | otherwise = readMaybe =<< confRaw :: Maybe Int
                obj' = case ( confInt
                            , readMaybe =<< lookupString "evidence"   meta :: Maybe Int
                            ) of
                    (Just conf, Just ev) ->
                        let raw :: Double
                            raw   = fromIntegral conf     / 100.0 * 0.6
                                  + fromIntegral (ev - 1) / 4.0   * 0.4
                            score = max 0 (min 100 (round (raw * 100.0) :: Int))
                        in  Map.insert "score" (show score) obj
                    _ -> obj
            if Map.null obj'
                then return Nothing
                else return (Just (url, obj'))
  where
    grab name meta = case lookupString name meta of
        Just v  -> Just (name, v)
        Nothing -> Nothing


-- ---------------------------------------------------------------------------
-- Bibliography helpers (Phase 6b)
-- ---------------------------------------------------------------------------

-- | Invert a @citekey -> BibExtra@ map into @keyword -> [citekey]@
--   using each entry's 'bibKeywords' list as the inversion source.
invertKeywordsBib :: Map String BibExtra -> Map String [String]
invertKeywordsBib =
    Map.fromListWith (++) . concatMap flatten . Map.toList
  where
    flatten (k, e) = [ (kw, [k]) | kw <- bibKeywords e ]

-- | Read a @keywords:@ frontmatter field, accepting YAML list and
--   comma-separated scalar forms. Matches 'Contexts.keywordLinksField'.
readKeywords :: Metadata -> [String]
readKeywords meta = filter (not . null) . map trimSpaces $
    case lookupStringList "keywords" meta of
        Just xs -> xs
        Nothing -> case lookupString "keywords" meta of
            Just s  -> splitComma s
            Nothing -> []
  where
    trimSpaces = dropWhile (== ' ') . reverse . dropWhile (== ' ') . reverse
    splitComma s = case break (== ',') s of
        (before, [])      -> [before]
        (before, _ : rest) -> before : splitComma rest

-- | Invert a @[(Identifier, [keyword])]@ association into
--   @keyword -> [Identifier]@. Identifiers can appear under multiple
--   keywords (multi-keyword items).
invertKeywordsWritings :: [(Identifier, [String])] -> Map String [Identifier]
invertKeywordsWritings pairs =
    Map.fromListWith (++)
        [ (kw, [ident]) | (ident, kws) <- pairs, kw <- kws ]

-- | Sort citekeys for the /bibliography/ index: ascending first-author
--   surname, year-descending within author.
bibliographyIndexOrder :: Map String BibExtra -> [String]
bibliographyIndexOrder extras =
    map fst $ sortBy (comparing sortKey) (Map.toList extras)
  where
    sortKey (_, e) = (firstAuthorSurname e, Down (bibYear e))

-- | Sort citekeys for a /bibliography/<kw>/ References section: year
--   descending, then alphabetical by first-author surname within the
--   year. Filtered to only entries whose 'bibKeywords' includes @kw@.
keywordReferencesOrder :: Map String BibExtra -> String -> [String]
keywordReferencesOrder extras kw =
    map fst $ sortBy (comparing sortKey)
        [ (k, e) | (k, e) <- Map.toList extras, kw `elem` bibKeywords e ]
  where
    sortKey (_, e) = (Down (bibYear e), firstAuthorSurname e)

-- | Identifier of a bibliography-meta sidecar for a given keyword.
--   Parallels 'Tags.sidecarIdentifier' but under
--   @content/bibliography-meta/@ rather than @content/tag-meta/@.
bibliographyMetaIdentifier :: String -> Identifier
bibliographyMetaIdentifier kw =
    fromFilePath ("content/bibliography-meta/" ++ kw ++ ".md")

-- | Group an alphabetically-sorted list of citekeys into letter buckets
--   keyed by the uppercase first letter of each entry's first-author
--   surname (falling back to the citekey's first letter when no author
--   was parsed — edge case, shouldn't occur in current content).
--
--   Because @sortedKeys@ is already alphabetical, 'Data.List.groupBy'
--   produces contiguous same-letter runs in one pass.
groupByLetter :: Map String BibExtra -> [String] -> [(Char, [String])]
groupByLetter extras sortedKeys =
    let withLetters = [ (k, letterOf k) | k <- sortedKeys ]
        grouped     = groupBy (\(_, a) (_, b) -> a == b) withLetters
    in  [ (letter, map fst grp) | grp <- grouped
                                , (_, letter) : _ <- [grp] ]
  where
    letterOf k =
        let e = fromMaybe emptyBibExtra (Map.lookup k extras)
        in case firstAuthorSurname e of
            (c:_) -> toUpper c
            _     -> case k of
                (c:_) -> toUpper c
                _     -> '?'

-- | The A–Z jump strip above the entry list. Present letters render as
--   anchor links to their section heading; absent letters render as
--   muted, non-linked spans so the alphabet reads as a complete strip
--   regardless of content gaps.
renderBibliographyAlphabet :: [Char] -> T.Text
renderBibliographyAlphabet presentList =
    let present = Set.fromList presentList
        cell c
          | c `Set.member` present =
              "<a href=\"#" <> T.singleton c
              <> "\" class=\"alpha\">" <> T.singleton c <> "</a>"
          | otherwise =
              "<span class=\"alpha alpha-empty\" aria-hidden=\"true\">"
              <> T.singleton c <> "</span>"
    in  "<nav class=\"bibliography-alphabet\" aria-label=\"Jump to letter\">"
     <> T.concat (map cell ['A' .. 'Z'])
     <> "</nav>\n"

-- | Letter-group heading inserted between entry groups on the
--   bibliography index. The @id@ is the anchor target for
--   'renderBibliographyAlphabet' jump-links.
renderLetterHeader :: Char -> T.Text
renderLetterHeader c =
    "<h2 id=\"" <> T.singleton c
    <> "\" class=\"bibliography-letter\">"
    <> T.singleton c <> "</h2>\n"

-- | Item-level context for Writings-section cards on a keyword page.
--   Same fields as the library's 'portalItemCtx' but with tag-footer
--   suppression tuned to the keyword context rather than a portal
--   (nothing to suppress here — writings keep their full tag list so
--   readers can see the item's own portal filings).
portalWritingCtx :: String -> Context String
portalWritingCtx _kw =
    contentKindField
    <> constField "full-abstract" "true"
    <> essayCtx

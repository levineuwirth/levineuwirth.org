{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
module Site (rules, siteConfiguration) where

import Control.Monad (forM, forM_, void, when)
import Control.Monad.Except (catchError)
import Data.Char     (isSpace, toLower, toUpper)
import Data.List     (groupBy, isPrefixOf, isSuffixOf, sort, sortBy, stripPrefix)
import Data.Map.Strict (Map)
import Data.Maybe    (catMaybes, fromMaybe, listToMaybe)
import Data.Ord      (Down (..), comparing)
import Data.Set      (Set)
import qualified Data.Set as Set
import qualified Data.Text as T
import Data.Time.Clock (getCurrentTime)
import Data.Time.Format (defaultTimeLocale, formatTime)
import System.Directory (listDirectory)
import System.Environment (lookupEnv)
import System.FilePath (splitDirectories, takeDirectory, takeFileName, takeExtension,
                        replaceExtension, (</>))
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
                   tagLinksFieldExcludingTopSegment, isProvedConfidence,
                   canonicalUrlPath, feedMetaFields, identifierDisplayUTC)
import qualified Filters.SourceRefs as SR
import qualified Patterns as P
import Photography (photographyRules)
import Tags       (buildAllTags, applyTagRules, sidecarIdentifier,
                   portalIntroField, portalTooltipField)
import Pagination (blogPaginateRules)
import Stats      (statsRules)

-- ---------------------------------------------------------------------------
-- Publication boundary
-- ---------------------------------------------------------------------------

-- | Hakyll provider configuration.
--
--   @.gitignore@ and this function protect two different things and
--   neither substitutes for the other: @.gitignore@ keeps a file out of
--   *commits*; 'ignoreFile' keeps it out of the *deployment*. A file Git
--   ignores is still sitting in the provider directory, and the broad
--   rules below (@static\/**@, the co-located essay-asset rule, the
--   per-page JS rule) would otherwise turn it into an identifier, route
--   it, and copy it into @_site\/@ — from where @make deploy@ rsyncs it
--   to the public document root. A probe confirmed exactly that for a
--   @.key@ file and a @.local.md@ note, both correctly Git-ignored.
--
--   Ignoring at the provider boundary is stronger than excluding at each
--   rule: an ignored path never becomes an identifier at all, so no
--   present or future rule, listing, feed, search index, or @\/source\/@
--   copy can reach it.
--
--   The patterns mirror the credential / private-note / editor-junk block
--   of @.gitignore@; the two lists are meant to agree, so extend both.
--   Hakyll's own defaults (dotfiles, @#…#@ autosaves, @…~@ backups,
--   @.swp@) are preserved by delegating to 'defaultConfiguration' first
--   rather than replacing the function.
siteConfiguration :: Configuration
siteConfiguration = defaultConfiguration
    { ignoreFile = \path ->
        ignoreFile defaultConfiguration path || neverPublish path
    }

-- | Paths that must never become Hakyll identifiers. See
--   'siteConfiguration'.
neverPublish :: FilePath -> Bool
neverPublish path =
       "__pycache__" `elem` splitDirectories path
    || any (`isSuffixOf` name) suffixes
    || any (`isPrefixOf` name) prefixes
    || name `elem` exactNames
  where
    name = takeFileName path

    suffixes =
        -- Private working notes and unfinished drafts.
        [ ".local.md", ".draft.md"
        -- Key material and credential bundles.
        , ".key", ".pem", ".p12", ".pfx", ".env"
        -- Editor and interpreter junk.
        , "~", ".swp", ".swo", ".pyc", ".pyo"
        -- Interrupted or in-flight writes.
        , ".tmp", ".part"
        ]

    prefixes =
        -- id_rsa, id_rsa.pub, id_ed25519, credentials.json, .env.local, …
        [ "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "credentials", ".env." ]

    -- Dotfiles are already covered by Hakyll's default predicate; naming
    -- them keeps the intent legible if that default ever changes.
    exactNames =
        [ ".env", ".DS_Store", ".netrc", ".npmrc", ".pypirc" ]

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

-- | Item context shared by both Atom feeds.
--
--   Three timestamps, three meanings (audit F11):
--
--     * @published@ — the creation date. Never moves.
--     * @updated@   — the most recent /substantive/ revision, from the
--                     @revised:@ frontmatter the cards already read
--                     ('itemDisplayUTC'), falling back to the creation
--                     date for a piece that has not been revised.
--     * the build time — kept out of both. A rebuild is not a revision,
--       and stamping one here would push every entry to the top of every
--       subscriber's reader on every deploy.
--
--   Before this, @updated@ was @dateField@ — the creation date — so the
--   branch-capture essay advertised its July original as its September
--   revision and no subscriber could see that it had changed.
feedCtx :: Context String
feedCtx =
    feedMetaFields
    <> bodyField "description"
    <> defaultContext

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

    -- Static-image dimension sidecars (@static\/images\/foo.jpg.dims.yaml@).
    --
    -- Excluded from the copy rule above (they are compile-time inputs, not
    -- deliverables), which left them claimed by no rule at all and so
    -- outside Hakyll's universe — where a pattern dependency naming them
    -- could never fire, because the modified set is intersected with the
    -- claimed identifiers. Matched here without a route for exactly the
    -- reason the essay sidecars are: to make them trackable. Audit B11.
    match "static/**/*.dims.yaml" $ compile getResourceLBS

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
    --
    -- @data/@ is named file-by-file rather than by glob. The former
    -- @data/*.json@ swept in whatever happened to be sitting in that
    -- directory — build state (@archive-state.json@), the search index
    -- metadata, and any private JSON a future tool drops there — and
    -- published it under @/source/@. 'publicDataJson' is the explicit
    -- allowlist; 'Filters.SourceRefs.publicDataJson' is the same list, so
    -- the link-emitting heuristic and the serving rule cannot drift.
    --
    -- @checklist.md@ is deliberately absent: .gitignore calls it a local
    -- working/planning document, and it was nonetheless being served in
    -- full at /source/checklist.md.
    -- ---------------------------------------------------------------------------
    let sourcePreviewable =
                 "build/**.hs"
            .||. "static/js/**"
            .||. "static/css/**"
            .||. "templates/**"
            .||. "tools/**.sh"
            .||. "tools/**.py"
            .||. "nginx/**.conf"
            .||. fromList (map (fromFilePath . ("data/" ++)) SR.publicDataJson)
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

    -- Bibliography inputs — the @.bib@ databases and the CSL style.
    --
    -- Matched (not routed) so that every consumer can 'load' them and get
    -- real dependency tracking. Everything that renders bibliography HTML
    -- reads these through citeproc inside 'unsafeCompiler', which Hakyll
    -- cannot see; before this rule the CSL file was claimed by no rule at
    -- all and the @.bib@ files only in their @"source-preview"@ version,
    -- so neither could ever be a dependency. (See the note above the
    -- @*.dims.yaml@ rule: an identifier no rule claims never enters
    -- Hakyll's universe, and a dependency on it can never fire.)
    --
    -- Consumers: the essay pipeline (Compilers.trackBibliographyInputs)
    -- and the synthetic /bibliography/ index and keyword pages below.
    match ("data/*.bib" .||. "data/*.csl") $ compile getResourceString

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
    -- Co-located score fragments are inlined by Filters.Score inside
    -- 'unsafeCompiler' — Hakyll sees the page depending on index.md and
    -- nothing else, so re-engraving a score left the page serving the old
    -- SVG (audit B11; the essay figure dependency above is the model). The
    -- SVGs are already claimed by the copy rules further down, so naming
    -- them in a pattern dependency is all that is needed here.
    scoreDep <- makePatternDependency $
                      "content/me/scores/*.svg"
                 .||. "content/memento-mori/scores/*.svg"

    -- me/index.md — compiled as a full essay (TOC, metadata block, sidenotes).
    -- Lives in its own directory so co-located SVG score fragments resolve
    -- correctly: the Score filter reads paths relative to the source file's
    -- directory (content/me/), not the content root.
    rulesExtraDependencies [scoreDep] $ match "content/me/index.md" $ do
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
    rulesExtraDependencies [scoreDep] $ match "content/memento-mori/index.md" $ do
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
    -- Figures are executed at compile time by Filters.Viz, but nothing in
    -- Hakyll's graph connects an essay to the scripts and data those figures
    -- read: the page depends on index.md alone. Editing a benchmark CSV
    -- therefore republished the *data file* (it is copied by the asset rule
    -- below) while leaving the chart drawn from it untouched — a page whose
    -- figure contradicts the numbers sitting next to it, with nothing said
    -- on stdout. tools/build-freshness.sh does not cover this either: it
    -- hashes build/**/*.hs, not content assets or tools/.
    --
    -- tools/viz_theme.py is in the pattern for the same reason. Every figure
    -- script imports it, so a change to the shared theme has to invalidate
    -- every page that draws one.
    --
    -- This is deliberately coarse: one dependency for all essays, so any
    -- figure edit rebuilds every essay rather than only its own. At the
    -- current corpus that is a few seconds and it cannot be wrong. Making it
    -- per-essay is worth doing when figure count makes it hurt, and wants the
    -- content-addressed cache alongside it.
    -- The same hole, one filter over: Filters.Images reads *.dims.yaml
    -- sidecars at compile time to attach width/height. Verified before the
    -- fix — editing a sidecar from width: 1176 to width: 999 and rebuilding
    -- left the page byte-identical, still serving the old dimensions. Milder
    -- than the figure case (a wrong layout hint, not a wrong claim) but the
    -- same silence, so it belongs in the same dependency.
    figureDep <- makePatternDependency $
                      "content/essays/**/figures/**"
                 .||. "content/drafts/essays/**/figures/**"
                 .||. "content/essays/**/*.dims.yaml"
                 .||. "content/drafts/essays/**/*.dims.yaml"
                 -- Essays embed site-wide images from /images/; their
                 -- dimension sidecars live under static/ and are read by
                 -- the same filter (B11).
                 .||. "static/**/*.dims.yaml"
                 .||. "tools/viz_theme.py"

    rulesExtraDependencies [figureDep] $ match allEssays $ do
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

    -- Dimension sidecars: tracked, but not shipped.
    --
    -- These are consumed by Filters/Images.hs at compile time, so the asset
    -- rule below deliberately excludes them from _site — which left them
    -- matched by no rule at all, and therefore outside Hakyll's universe.
    -- A makePatternDependency naming them was consequently inert. Hakyll
    -- computes its modified set as
    --   Set.filter (resourceModified provider) (Map.keysSet universe)
    -- (Core/Runtime.hs), and the universe is the identifiers some rule
    -- claims — so an unclaimed file can never enter it, and a dependency
    -- pointing at one can never fire. tools/viz_theme.py works in that same
    -- dependency only because "tools/**.py" is claimed by the source-preview
    -- rule above.
    --
    -- Compiling with no route registers them as tracked inputs and writes
    -- nothing.
    match "content/essays/**/*.dims.yaml" $ compile getResourceLBS
    when isDev $
        match "content/drafts/essays/**/*.dims.yaml" $ compile getResourceLBS

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

    -- Collection index pages (e.g. content/poetry/shakespeare-sonnets/index.md).
    -- See 'collectionCtx' and 'isPublishedCollection' for the rendering
    -- contract and the scaffold gate (audit C05).
    matchMetadata "content/poetry/*/index.md" (isPublishedCollection isDev) $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ do
            ctx <- collectionCtx P.poetryPattern poetryCtx pageCtx
            pageCompiler
                >>= loadAndApplyTemplate "templates/collection.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"    ctx
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
    matchMetadata "content/fiction/*/index.md" (isPublishedCollection isDev) $ do
        route   $ stripPrefixRoute "content/"
                  `composeRoutes` setExtension "html"
        compile $ do
            ctx <- collectionCtx P.fictionPattern fictionCtx pageCtx
            pageCompiler
                >>= loadAndApplyTemplate "templates/collection.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"    ctx
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
    --
    -- Same unsafeCompiler blind spot as the me/ and memento-mori score
    -- fragments (B11): Filters.Score reads content/music/<slug>/scores/*.svg
    -- relative to the source file. The SVG copy rule above claims them, so
    -- the dependency can fire.
    musicScoreDep <- makePatternDependency "content/music/**/*.svg"

    rulesExtraDependencies [musicScoreDep] $ match "content/music/*/index.md" $ do
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
                    -- C01: an explicit description, ahead of siteCtx's
                    -- fallback. Left to the fallback, a list page's
                    -- description is the first *item's* opening
                    -- paragraph, which describes one essay and claims
                    -- to describe the index.
                    <> constField "description"
                        "Every essay published here, newest first."
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
                    <> constField "description"
                        "Every poem published here, newest first."
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
                    <> constField "description"
                        "Every piece of fiction published here, newest first."
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
                   <> constField "description"
                        "Everything published or revised here, newest first."
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
                   <> constField "description"
                        ("Everything on this site, arranged by shelf: essays, "
                         ++ "fiction, poetry, music, photography, and research.")
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
    -- Register data/*.bib + data/*.csl as tracked inputs of a synthetic
    -- bibliography page.
    --
    -- 'bibFilePaths' and 'bibExtrasAll' above are read at rule-generation
    -- time through 'preprocess', and the entry HTML is rendered by
    -- citeproc inside 'unsafeCompiler'. Both are invisible to Hakyll, so
    -- an edit to a .bib title updated the essays that cite it and left
    -- /bibliography/ serving its cached copy. 'loadAll' both registers a
    -- pattern dependency (a new or deleted .bib file changes the match
    -- set) and depends on each matched identifier (an edited .bib file is
    -- out of date), which is what forces the recompile. The loaded bodies
    -- are deliberately unused — 'renderBibliographyHtml' re-reads the
    -- files itself, because citeproc wants paths, not contents.
    let trackBibInputs :: Compiler ()
        trackBibInputs = void
            (loadAll (("data/*.bib" .||. "data/*.csl") .&&. hasNoVersion)
                :: Compiler [Item String])

    create ["bibliography/index.html"] $ do
        route idRoute
        compile $ do
            trackBibInputs
            let sortedKeys = bibliographyIndexOrder bibExtrasAll
                grouped    = groupByLetter bibExtrasAll sortedKeys
                present    = map fst grouped
            html <- unsafeCompiler $ do
                parts <- forM grouped $ \(letter, keys) -> do
                    body <- renderBibliographyHtml bibFilePaths bibExtrasAll keys
                    return (renderLetterHeader letter <> body)
                return (renderBibliographyAlphabet present <> T.concat parts)
            -- C07: entry math is rendered to MathML at build time by
            -- 'Citations.renderEntries', so this page needs no runtime
            -- typesetter. The guard is a safety net: if the MathML writer
            -- ever declines a construct it falls back to a raw
            -- `class="math …"` span holding LaTeX source, and a page with
            -- one of those does need KaTeX after all. Nothing currently in
            -- the corpus trips it.
            let needsKatex =
                    any (`T.isInfixOf` html)
                        ["class=\"math inline\"", "class=\"math display\""]
                mathFld | needsKatex = constField "math" "true"
                        | otherwise  = mempty
            let ctx = constField "title"          "Bibliography"
                   <> constField "bibliography-index" "true"
                   <> constField "description"
                        ("Every work cited across this site, in one list, "
                         ++ "alphabetical by author.")
                   <> mathFld
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
                trackBibInputs
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
                -- Same MathML-fallback guard as the bibliography index.
                let needsKatex =
                        any (`T.isInfixOf` refsHtml)
                            ["class=\"math inline\"", "class=\"math display\""]
                    mathFld | needsKatex = constField "math" "true"
                            | otherwise  = mempty
                let referencesCtx
                        | null refKeys = mempty
                        | otherwise =
                            constField "references" (T.unpack refsHtml)
                            <> mathFld

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
            renderAtom musicFeedConfig feedCtx compositions
                >>= repairEmptyFeedUpdated (null compositions)

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
            --
            -- /proxy/ *is* disallowed, and for the opposite reason. Those
            -- locations (nginx/popup-proxy.conf) fetch and re-serve
            -- third-party pages — arXiv, archive.org, PubMed — under this
            -- origin so the hover popups can read them same-origin. They
            -- are a reading affordance, not this site's content: indexing
            -- them would put someone else's pages in the index under
            -- levineuwirth.org URLs. Unlike the archive wrappers there is
            -- no HTML of ours to carry a noindex meta, so robots.txt is
            -- the only control available at build time.
            [ "User-agent: *"
            , "Allow: /"
            , "Disallow: /proxy/"
            , ""
            , "Sitemap: https://levineuwirth.org/sitemap.xml"
            ]

    -- ---------------------------------------------------------------------------
    -- 404.html — custom not-found page.
    --
    -- nginx/vhost.conf.example declares `error_page 404 /404.html` and
    -- serves it with the 404 status; nothing generated the file, so the
    -- deployment fell back to nginx's stock response with no navigation
    -- and no way back into the site. Rendered through the ordinary page
    -- shell so the reader keeps the nav, search, and footer, and marked
    -- noindex so the error page itself never enters an index.
    -- ---------------------------------------------------------------------------
    create ["404.html"] $ do
        route idRoute
        compile $ do
            let ctx = constField "title"   "Page not found"
                   <> constField "noindex" "true"
                   <> constField "description"
                        "No page exists at this address."
                   -- Keeps the body out of the keyword index; see the
                   -- comment in templates/page.html.
                   <> constField "search-exclude" "true"
                   <> pageCtx
            -- Deliberately NOT relativized. Every other page is rewritten
            -- to root-relative-from-here URLs, which is correct because
            -- each is served from its own path. The 404 body is served
            -- for *any* missing path, so `./css/base.css` would resolve
            -- against whatever directory the reader mistyped. Absolute
            -- URLs are the only form that works from every depth.
            makeItem ""
                >>= loadAndApplyTemplate "templates/404.html"     ctx
                >>= loadAndApplyTemplate "templates/default.html" ctx

    -- ---------------------------------------------------------------------------
    -- sitemap.xml — every dated content page (essays, blog, poetry, fiction,
    -- music) plus the photography section and the standalone pages.
    --
    -- The previous version listed only the 22 dated writing pages, on the
    -- reasoning that a page without `date:` would force an invented
    -- `lastmod`. That trade was the wrong way round: `lastmod` is optional
    -- per the sitemaps protocol, so a page with no known revision date can
    -- simply be listed without one — whereas leaving 400-odd photography
    -- URLs and every standalone page out of the sitemap entirely is a real
    -- omission on a media-heavy site.
    --
    -- Deliberately excluded, and why:
    --   * drafts                — unpublished (they are also dev-only)
    --   * /source/              — raw source copies, not readable pages
    --   * /archive/             — wrappers already carry `noindex`
    --   * feeds, search, JSON   — not HTML documents a reader lands on
    --   * tag / author / keyword indexes — list variants of pages that are
    --     already here under their own canonical URLs
    --   * content/library.md    — an intro fragment with no route of its
    --     own (it is snapshot-loaded into /library.html)
    -- ---------------------------------------------------------------------------
    create ["sitemap.xml"] $ do
        route idRoute
        compile $ do
            -- Dated writing. P.essayPattern, not `allEssays`: drafts stay
            -- out of the sitemap even in a dev build.
            datedIds <- getMatches $
                (    P.essayPattern
                .||. P.blogPattern
                .||. P.fictionPattern
                .||. P.poetryPattern
                .||. P.musicPattern
                ) .&&. hasNoVersion

            -- Every photographic entry: flat frames, series landings, and
            -- the sibling frames inside a series.
            photoIds <- getMatches (P.allPhotoEntries .&&. hasNoVersion)

            -- Generated photography indexes: /photography/by-year/,
            -- /photography/by-year/<year>/, /photography/map/,
            -- /photography/contact-sheet/. These are `create`d, so their
            -- identifier is their route; map.json and feed.xml are dropped
            -- by the .html filter.
            photoIndexIds <- filter (isHtmlIdentifier . toFilePath)
                                <$> getMatches ("photography/**" .&&. hasNoVersion)

            -- CV routing pages (/cv/<slug>/).
            cvIds <- getMatches ("content/cv/*.md" .&&. hasNoVersion)

            let standaloneIds = map fromFilePath
                    -- Authored standalone pages.
                    [ "content/about.md"            -- /about.html (vita)
                    , "content/work.md"
                    , "content/links.md"
                    , "content/gpg.md"
                    , "content/colophon.md"
                    , "content/current.md"
                    , "content/commonplace.md"
                    , "content/me/index.md"
                    , "content/memento-mori/index.md"
                    -- Section landings.
                    , "content/photography/index.md"
                    , "content/music/index.md"
                    -- Generated landings and indexes.
                    , "essays/index.html"
                    , "poetry/index.html"
                    , "fiction/index.html"
                    , "library.html"
                    , "new.html"
                    , "bibliography/index.html"
                    ]

                corpus = datedIds ++ photoIds ++ photoIndexIds
                      ++ cvIds ++ standaloneIds

            entries <- sitemapEntries corpus

            let siteRoot = "https://levineuwirth.org"
                sitemapItemCtx =
                    constField "root" siteRoot
                    <> field "url" (return . fst . itemBody)
                    <> field "lastmod"
                        (maybe (noResult "no known revision date") return
                            . snd . itemBody)
                sitemapCtx =
                    constField "root" siteRoot
                    <> listField "entries" sitemapItemCtx (return entries)
            makeItem ("" :: String)
                >>= loadAndApplyTemplate "templates/sitemap.xml" sitemapCtx

-- ---------------------------------------------------------------------------
-- Compile-time filesystem reads and their dependency coverage (audit B11)
-- ---------------------------------------------------------------------------
--
-- Several filters read the filesystem from inside 'unsafeCompiler', which
-- is invisible to Hakyll's dependency graph: the compiled page depends on
-- its Markdown source and on nothing those filters touched. The inventory
-- below is the full list, so that the next filter added here has somewhere
-- to declare itself rather than quietly joining the untracked set.
--
-- Covered by an explicit dependency:
--
--   * "Filters.Viz" figure scripts and their data, plus @tools/viz_theme.py@
--     — 'figureDep', over every essay. Coarse on purpose: one dependency
--     for all essays.
--   * @*.dims.yaml@ sidecars read by "Filters.Images" — 'figureDep' for
--     essays and @static/@; a sibling dependency in "Photography" for the
--     photography corpus. Both needed a matched-but-unrouted rule first:
--     Hakyll intersects its modified set with the identifiers some rule
--     claims, so a dependency on an unclaimed file can never fire.
--   * Score fragments read by "Filters.Score" — 'scoreDep' (me/,
--     memento-mori/) and 'musicScoreDep' (music compositions). Essay score
--     fragments live under @content/essays/**/figures/**@ or beside the
--     essay and are carried by 'figureDep'.
--   * @.bib@ databases and the CSL style read by citeproc —
--     'Compilers.trackBibliographyInputs' per page, and 'trackBibInputs'
--     for the synthetic bibliography pages.
--   * @data/*.yaml@, @yaml-source/data/*.yml@, @data/build-stamp.txt@ —
--     matched (unrouted) and 'load'ed by their consumers.
--
-- Deliberately not covered, and why:
--
--   * "Filters.SourceRefs" probes @doesFileExist@ for every repository
--     path mentioned in prose, to decide whether to emit a @/source/@
--     hover link. The interesting change is a file appearing or
--     disappearing, which changes the /match set/ of the source-preview
--     rule and is therefore a rule-generation input, not a compiler input.
--     A pattern dependency over the whole source-previewable corpus would
--     rebuild every page on any edit to any @.hs@, @.js@, or @.css@ file —
--     an entire-site rebuild on every commit, to keep one hover link
--     honest. The seven-day full-build fallback bounds the staleness.
--   * "ArchiveIndex" reads @archive/manifest.yaml@ and
--     @data/archive-state.json@ once per process and caches the result in
--     a CAF, so a watch session does not see archive state change until it
--     is restarted. Left as is deliberately (it is what keeps the archive
--     filter from re-reading the manifest on every link of every page);
--     the workaround is to restart @make watch@ after an archive edit.
--   * Blog, poetry, and fiction entries can in principle carry figures and
--     score fragments; none currently do, and neither section has a
--     figures/ directory. Add them to 'figureDep' if that changes.
--   * @tools/embed.py@ output (@data/similar-links.json@) is matched and
--     loaded, but is written *after* Hakyll runs (audit B01) — a build
--     order problem, not a dependency-tracking one.

-- ---------------------------------------------------------------------------
-- Collections (poetry / fiction landing pages)
-- ---------------------------------------------------------------------------

-- | Context for a collection landing page: the ordinary page fields plus
--   the collection's own children.
--
--   @childPattern@ is the section's entry pattern (which already excludes
--   @index.md@); it is intersected with a glob for /this/ collection's
--   directory, so a landing page lists its siblings and nothing else.
--   Entries are ordered by display date, newest first — the same ordering
--   the library and @\/new.html@ use, so a revised poem does not sort
--   under its original date on one surface and its revision date on
--   another.
--
--   @has-collection-entries@ gates the template's empty state. An empty
--   'listField' renders as nothing at all rather than as "no items", which
--   is how the reader ended up with a landing page that promised child
--   links and showed none.
collectionCtx :: Pattern            -- ^ the section's entry pattern
              -> Context String     -- ^ context for a child entry
              -> Context String     -- ^ context for the landing page itself
              -> Compiler (Context String)
collectionCtx childPattern childCtx baseCtx = do
    ident <- getUnderlying
    let dir = takeDirectory (toFilePath ident)
    children <- recentFirstByDisplay
                    =<< loadAll (childPattern
                                  .&&. fromGlob (dir ++ "/*.md")
                                  .&&. hasNoVersion)
    let entriesFld
            | null children = mempty
            | otherwise =
                  listField "collection-entries" childCtx (return children)
                  <> constField "has-collection-entries" "true"
    return (entriesFld <> constField "collection" "true" <> baseCtx)

-- | Is a collection landing page fit to publish?
--
--   @draft: true@ marks a collection index that is still authoring
--   scaffolding — placeholder prose telling the author what to write.
--   Audit C05 found exactly that live at @\/poetry\/selected-verse\/@.
--   Such a page gets no route in a production build, which also keeps it
--   out of every listing, the sitemap, the feeds, and the search index,
--   because all of those are built from routed identifiers. @SITE_ENV=dev@
--   builds it as usual so the author can see the scaffold while working.
--
--   Deliberately a separate key from @status:@, which is the epistemic
--   peer-review state read by "Marks", and from @content\/drafts\/@, which
--   is a directory of unfinished essays.
isPublishedCollection :: Bool -> Metadata -> Bool
isPublishedCollection dev meta = dev || not isDraft
  where
    isDraft = case lookupString "draft" meta of
        Just v  -> map toLower (filter (not . isSpace) v) `elem` ["true", "yes", "1"]
        Nothing -> False

-- ---------------------------------------------------------------------------
-- Sitemap
-- ---------------------------------------------------------------------------

-- | Turn a list of identifiers into @(url, maybe lastmod)@ sitemap rows.
--
--   Identifiers with no route are dropped (an unrouted sidecar is not a
--   page), duplicates are collapsed, and the site root is dropped because
--   @templates\/sitemap.xml@ emits it unconditionally. Rows come back in
--   URL order, which keeps the generated file stable across builds.
sitemapEntries :: [Identifier] -> Compiler [Item (String, Maybe String)]
sitemapEntries idents = do
    rows <- mapM sitemapEntry idents
    let unique = Map.toAscList (Map.fromList
                    [ (u, d) | Just (u, d) <- rows, u /= "/" ])
    return [ Item (fromFilePath u) (u, d) | (u, d) <- unique ]

-- | One sitemap row, or 'Nothing' when the identifier has no route.
sitemapEntry :: Identifier -> Compiler (Maybe (String, Maybe String))
sitemapEntry ident = do
    mRoute <- getRoute ident
    case mRoute of
        Nothing -> return Nothing
        Just r  -> do
            -- `lastmod` is optional: a page with no `date:` is listed
            -- without one rather than dropped or given an invented date.
            -- getItemUTC throws for a created identifier that carries no
            -- metadata at all, which is the same "unknown" answer.
            --
            -- F11: the date is the *revision-aware* one, so a page that
            -- has been substantively revised advertises the revision
            -- rather than repeating its creation date to crawlers.
            -- 'identifierDisplayUTC' falls back to the creation date when
            -- there is no `revised:` entry.
            mDay <- fmap Just (formatTime defaultTimeLocale "%Y-%m-%d"
                                <$> identifierDisplayUTC ident)
                        `catchError` const (return Nothing)
            return (Just (canonicalUrlPath r, mDay))

-- | True for routes that name an HTML document. Used to keep @map.json@
--   and @feed.xml@ out of the photography-index sweep.
isHtmlIdentifier :: FilePath -> Bool
isHtmlIdentifier = isSuffixOf ".html"

-- ---------------------------------------------------------------------------
-- Feed repair
-- ---------------------------------------------------------------------------

-- | Give an empty Atom feed a valid @\<updated\>@ element.
--
--   Hakyll's 'renderAtom' derives the feed-level @updated@ from the first
--   item and falls back to the literal string @Unknown@ when the item
--   list is empty (@Hakyll.Web.Feed.renderFeed@). @Unknown@ is not an RFC
--   3339 timestamp, so the feed is invalid — and the music feed is
--   advertised unconditionally from @templates\/partials\/head.html@,
--   which means a reader's aggregator sees the broken document rather
--   than nothing at all. The catalog being empty is a legitimate state
--   (it is a young section), so the feed is kept and given the build
--   time: honest, well-formed, and it stops changing the moment the first
--   composition lands and a real entry date takes over.
--
--   No-op when the feed has entries, so a populated feed is never
--   restamped on every build.
repairEmptyFeedUpdated :: Bool -> Item String -> Compiler (Item String)
repairEmptyFeedUpdated False item = return item
repairEmptyFeedUpdated True  item = do
    stamp <- unsafeCompiler $
        formatTime defaultTimeLocale "%Y-%m-%dT%H:%M:%SZ" <$> getCurrentTime
    return $ fmap (replaceFirst placeholder ("<updated>" ++ stamp ++ "</updated>")) item
  where
    placeholder = "<updated>Unknown</updated>"

-- | Replace the first occurrence of a literal substring. Returns the
--   input unchanged when the needle is absent.
replaceFirst :: String -> String -> String -> String
replaceFirst needle replacement = go
  where
    go [] = []
    go s@(c:cs) = case stripPrefix needle s of
        Just rest -> replacement ++ rest
        Nothing   -> c : go cs

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

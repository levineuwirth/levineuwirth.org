{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Detect repo-relative source-file references in prose and wrap them
--   in a link that triggers a hover-preview popup of the file's contents.
--
--   Two trigger forms:
--
--   * Inline @\`build\/Filters\/Links.hs\`@ — Markdown inline code whose
--     text passes a conservative source-path heuristic.
--   * A Markdown link to
--     @https:\/\/git.levineuwirth.org\/neuwirth\/levineuwirth.org\/(src|raw)\/branch\/<branch>\/<path>@.
--
--   Both produce
--   @\<a class="source-ref" data-source-path="…" href="…">@. The href
--   points to the Forgejo source viewer so a click without JS — or a
--   popup that fails to fetch — still resolves to a useful target.
--   The popup provider in @static\/js\/popups.js@ fetches
--   @\/source\/\<path\>@ (a same-origin copy emitted by the Hakyll
--   source-preview rule in 'Site.rules') and renders a
--   syntax-highlighted snippet via Prism.
--
--   Conservative-by-design: the trigger only fires on paths the
--   @/source/@ serving rule actually publishes ('isServedPath', a
--   mirror of @sourcePreviewable@ in 'Site.rules'), or a small set of
--   named root files. This keeps the parser cheap, avoids false
--   positives on words that happen to contain a slash and a dot, and
--   guarantees every wrapped path has a fetchable @/source/…@ copy.
module Filters.SourceRefs (apply, isSourcePath, forgejoSourceUrl) where

import           Control.Monad        (when)
import           Data.IORef           (IORef, atomicModifyIORef', newIORef, readIORef)
import qualified Data.Map.Strict      as Map
import           Data.Text            (Text)
import qualified Data.Text            as T
import           System.Directory     (doesFileExist)
import           System.IO.Unsafe     (unsafePerformIO)
import           Text.Pandoc.Definition
import           Text.Pandoc.Walk     (walkM)

-- | Two passes: lift Forgejo source URLs in existing Markdown links
--   first, then wrap inline-code source paths. Both passes only add
--   the @source-ref@ class when it is not already present, so re-runs
--   are idempotent.
--
--   Runs in 'IO' because the heuristic confirms each candidate is a
--   real on-disk file before wrapping. This rules out paths like
--   @data/backlinks.json@ that look like source but are Hakyll build
--   artifacts produced into @_site/@ — wrapping those would emit a
--   link whose popup is guaranteed to 404.
apply :: Pandoc -> IO Pandoc
apply doc = do
    afterLinks <- walkM classifyExistingLink doc
    walkM wrapInlineCode afterLinks

-- | Inline @`path`@ → @\<a class="source-ref" data-source-path="path"\>\<code\>path\<\/code\>\<\/a\>@.
--   The original 'Code' node is preserved as the link's body so the
--   inline-code chrome (mono font, background) survives unchanged.
wrapInlineCode :: Inline -> IO Inline
wrapInlineCode orig@(Code (cIdent, cClasses, cKvs) txt)
    | "source-ref" `notElem` cClasses
    , isSourcePath txt = do
        exists <- existsCached txt
        if exists
            then pure $ Link
                    ( ""
                    , ["source-ref"]
                    , [ ("data-source-path", txt)
                      , ("target",           "_blank")
                      , ("rel",              "noopener noreferrer")
                      ]
                    )
                    [Code (cIdent, cClasses, cKvs) txt]
                    (forgejoSourceUrl txt, "")
            else pure orig
wrapInlineCode x = pure x

-- | Existing Markdown link to a Forgejo source URL on this site's git
--   host → tagged @source-ref@ and given a @data-source-path@ pointing
--   at the same path the popup provider expects.
classifyExistingLink :: Inline -> IO Inline
classifyExistingLink orig@(Link (ident, classes, kvs) ils (url, title))
    | "source-ref" `notElem` classes
    , Just path <- forgejoSourcePath url
    , isSourcePath path = do
        exists <- existsCached path
        if exists
            then pure $ Link
                    ( ident
                    , classes ++ ["source-ref"]
                    , kvs ++ [("data-source-path", path)]
                    )
                    ils (url, title)
            else pure orig
classifyExistingLink x = pure x

-- ---------------------------------------------------------------------------
-- Heuristic
-- ---------------------------------------------------------------------------

-- | True when the text looks like a repo-relative path that the
--   @/source/@ serving rule actually publishes (or is a whitelisted
--   root file), ends in a known source extension, and contains only
--   safe path characters. Conservative by design — the goal is no
--   false positives on prose that incidentally contains a slash and a
--   dot, and no wrapped path whose popup fetch would 404.
isSourcePath :: Text -> Bool
isSourcePath t = and
    [ not (T.null t)
    , T.all safeChar t
    , (isServedPath t && hasKnownExt t) || isKnownRootFile t
    ]
  where
    safeChar c =
           ('a' <= c && c <= 'z')
        || ('A' <= c && c <= 'Z')
        || ('0' <= c && c <= '9')
        || c == '/' || c == '.' || c == '_' || c == '-' || c == '+'

-- | Mirror of the @sourcePreviewable@ whitelist in 'Site.rules' (the
--   rule that copies files to @/source/<path>@) — the two must stay
--   aligned so every link this filter emits has a corresponding
--   @/source/…@ target for the popup to fetch. Directories Site.hs
--   does not serve (e.g. @content/@) are deliberately absent here:
--   wrapping them would emit popups that are guaranteed to 404.
isServedPath :: Text -> Bool
isServedPath t = or
    [ "build/"      `T.isPrefixOf` t && hasExt ".hs"
    , "static/js/"  `T.isPrefixOf` t
    , "static/css/" `T.isPrefixOf` t
    , "templates/"  `T.isPrefixOf` t
    , "tools/"      `T.isPrefixOf` t && (hasExt ".sh" || hasExt ".py")
    , "nginx/"      `T.isPrefixOf` t && hasExt ".conf"
    , "data/"       `T.isPrefixOf` t
        && not ("/" `T.isInfixOf` T.drop 5 t)   -- top-level data files only
        && (hasExt ".json" || hasExt ".yaml" || hasExt ".md" || hasExt ".bib")
    ]
  where
    hasExt e = e `T.isSuffixOf` T.toLower t

hasKnownExt :: Text -> Bool
hasKnownExt t =
    let lower = T.toLower t
    in  any (`T.isSuffixOf` lower)
            [ ".hs", ".js", ".mjs", ".css", ".html"
            , ".py", ".cabal", ".md", ".yaml", ".yml"
            , ".toml", ".sh", ".bash", ".svg", ".conf"
            , ".json", ".ini", ".tex", ".bib"
            ]

isKnownRootFile :: Text -> Bool
isKnownRootFile t = t `elem`
    [ "Makefile"
    , "levineuwirth.cabal"
    , "cabal.project", "cabal.project.freeze"
    , "pyproject.toml", "uv.lock"
    , "WRITING.md", "HOMEPAGE.md", "PHOTOGRAPHY.md", "README.md"
    , "LICENSE", "checklist.md"
    ]

-- ---------------------------------------------------------------------------
-- File existence cache
-- ---------------------------------------------------------------------------

-- | Process-wide memo of /positive/ @doesFileExist@ results, keyed by
--   the same path the popup will fetch. Hakyll runs this filter once
--   per compiled page and the same source-file references recur across
--   many pages (e.g. @build\/Filters\/Links.hs@ in the Links page,
--   the Colophon, several essays); the cache turns N stats into one
--   per distinct path. Only existence is memoized: a missing file is
--   re-stat'ed on every miss, so a source file created during a
--   long-lived @make watch@ session is picked up on the next rebuild
--   instead of staying "absent" for the process lifetime. (A file
--   /deleted/ mid-watch stays cached as present until restart — the
--   benign direction: the popup fetch 404s and simply never appears.)
--   The build process's working directory is the project root, so the
--   path can be passed straight to 'doesFileExist' without prefixing.
{-# NOINLINE existsCacheRef #-}
existsCacheRef :: IORef (Map.Map Text Bool)
existsCacheRef = unsafePerformIO (newIORef Map.empty)

existsCached :: Text -> IO Bool
existsCached path = do
    cache <- readIORef existsCacheRef
    case Map.lookup path cache of
        Just b  -> pure b
        Nothing -> do
            b <- doesFileExist (T.unpack path)
            when b $
                atomicModifyIORef' existsCacheRef (\m -> (Map.insert path b m, ()))
            pure b

-- ---------------------------------------------------------------------------
-- Forgejo URL helpers
-- ---------------------------------------------------------------------------

-- | Forgejo source-viewer URL for a repo-relative path. Pinned to the
--   @main@ branch so previews always reflect the deployed tip.
forgejoSourceUrl :: Text -> Text
forgejoSourceUrl path =
    "https://git.levineuwirth.org/neuwirth/levineuwirth.org/src/branch/main/"
    <> path

-- | Inverse of 'forgejoSourceUrl': extract the repo-relative path from
--   a Forgejo URL on this site's git host. Recognises both the
--   @\/src\/branch\/<b>\/@ web view and the @\/raw\/branch\/<b>\/@
--   variants. Returns 'Nothing' for any other URL.
forgejoSourcePath :: Text -> Maybe Text
forgejoSourcePath url = do
    rest <- T.stripPrefix repoBase url
    afterBranch <-
        case T.stripPrefix "src/branch/" rest of
            Just r  -> Just r
            Nothing -> T.stripPrefix "raw/branch/" rest
    let (_branch, slashAndPath) = T.breakOn "/" afterBranch
        path                    = T.drop 1 slashAndPath
    if T.null path then Nothing else Just path
  where
    repoBase = "https://git.levineuwirth.org/neuwirth/levineuwirth.org/"

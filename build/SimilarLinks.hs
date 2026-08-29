{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Similar-links field: injects a "Related" list into essay/page contexts.
--
-- @data/similar-links.json@ is produced by @tools/embed.py@ at build time
-- (called from the Makefile after pagefind, before sign).  It is a plain
-- JSON object mapping root-relative URL paths to lists of similar pages:
--
--   { "/essays/my-essay/": [{"url": "...", "title": "...", "score": 0.87}] }
--
-- This module loads that file with dependency tracking (so pages recompile
-- when embeddings change) and provides @similarLinksField@, which resolves
-- to an HTML list for the current page's URL.
--
-- If the file is absent (e.g. @.venv@ not set up, or first build) the field
-- returns @noResult@ — the @$if(similar-links)$@ guard in the template is
-- false and no "Related" section is rendered.
module SimilarLinks (similarLinksField) where

import           Data.Maybe                 (fromMaybe)
import qualified Data.ByteString            as BS
import qualified Data.Map.Strict            as Map
import           Data.Map.Strict            (Map)
import qualified Data.Text                  as T
import qualified Data.Text.Encoding         as TE
import qualified Data.Text.Encoding.Error   as TE
import qualified Data.Aeson                 as Aeson
import           Hakyll

-- ---------------------------------------------------------------------------
-- JSON schema
-- ---------------------------------------------------------------------------

data SimilarEntry = SimilarEntry
    { seUrl   :: String
    , seTitle :: String
    , seScore :: Double
    } deriving (Show)

instance Aeson.FromJSON SimilarEntry where
    parseJSON = Aeson.withObject "SimilarEntry" $ \o ->
        SimilarEntry
            <$> o Aeson..: "url"
            <*> o Aeson..: "title"
            <*> o Aeson..: "score"

-- ---------------------------------------------------------------------------
-- Context field
-- ---------------------------------------------------------------------------

-- | Maximum entries rendered in the "Related" block. The on-disk JSON may
-- contain more (embed.py's TOP_N); 'similarLinksField' caps the list
-- (@take maxSimilar@) before rendering.
maxSimilar :: Int
maxSimilar = 3

-- | Provides @$similar-links$@ (HTML list) and @$has-similar-links$@
-- (boolean flag for template guards).
-- Returns @noResult@ when the JSON file is absent, unparseable, or the
-- current page has no similar entries.
--
-- Note on normalisation: 'tools/embed.py' emits map keys using the live
-- site URL (e.g. @/essays/foo.html@ for a flat page, @/essays/foo/@ for a
-- directory-index page), while Hakyll's route gives @essays/foo.html@.
-- 'normaliseUrl' collapses both forms to a canonical stem, and we apply
-- it to every JSON key on load so the lookup cannot miss.
similarLinksField :: Context String
similarLinksField = field "similar-links" $ \item -> do
    -- Load with dependency tracking — pages recompile when the JSON changes.
    slItem <- load (fromFilePath "data/similar-links.json") :: Compiler (Item String)
    case Aeson.decodeStrict (TE.encodeUtf8 (T.pack (itemBody slItem)))
            :: Maybe (Map T.Text [SimilarEntry]) of
        Nothing  -> fail "similar-links: could not parse data/similar-links.json"
        Just rawMap -> do
            mRoute <- getRoute (itemIdentifier item)
            case mRoute of
                Nothing -> fail "similar-links: item has no route"
                Just r  ->
                    let normMap = Map.mapKeys (T.pack . normaliseUrl . T.unpack) rawMap
                        key     = T.pack (normaliseUrl ("/" ++ r))
                        entries = take maxSimilar (fromMaybe [] (Map.lookup key normMap))
                    in  if null entries
                        then fail "no similar links"
                        else return (renderSimilarLinks entries)

-- ---------------------------------------------------------------------------
-- URL normalisation (mirrors embed.py's URL derivation)
-- ---------------------------------------------------------------------------

normaliseUrl :: String -> String
normaliseUrl url =
    let t  = T.pack url
        -- strip query + fragment
        t1 = fst (T.breakOn "?" (fst (T.breakOn "#" t)))
        -- ensure leading slash
        t2 = if T.isPrefixOf "/" t1 then t1 else "/" `T.append` t1
        -- strip trailing index.html → keep the directory slash
        t3 = fromMaybe t2 (T.stripSuffix "index.html" t2)
        -- strip bare .html extension only for non-index pages
        t4 = fromMaybe t3 (T.stripSuffix ".html" t3)
    in  percentDecode (T.unpack t4)

-- | Percent-decode @%XX@ escapes (UTF-8) so percent-encoded paths
-- collide with their decoded form on map lookup. Mirrors
-- 'Backlinks.percentDecode' (and 'Backlinks.normaliseUrl' now applies
-- the same strip-@index.html@-then-@.html@ normalisation as this
-- module); the duplication keeps the two modules dependency-free of
-- each other.
percentDecode :: String -> String
percentDecode = T.unpack . TE.decodeUtf8With TE.lenientDecode . BS.pack . go
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

-- | Percent-encode a string for use as a URI query value: RFC 3986
-- unreserved characters pass through; everything else — including @&@,
-- @?@, @#@, spaces, and non-ASCII text via its UTF-8 bytes — becomes
-- @%XX@. Hand-rolled (the moral equivalent of network-uri's
-- @escapeURIString isUnreserved@) because network-uri is not otherwise
-- a dependency. The output is also HTML-attribute-safe: it contains
-- only unreserved characters and @%XX@ escapes.
percentEncode :: String -> String
percentEncode = concatMap enc . BS.unpack . TE.encodeUtf8 . T.pack
  where
    enc b
        | unreserved b = [toEnum (fromIntegral b)]
        | otherwise    = ['%', hexDigit (b `div` 16), hexDigit (b `mod` 16)]
    unreserved b =
        let c = toEnum (fromIntegral b) :: Char
        in     (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')
            || (c >= '0' && c <= '9') || c `elem` ("-._~" :: String)
    hexDigit n = "0123456789ABCDEF" !! fromIntegral n

-- ---------------------------------------------------------------------------
-- HTML rendering
-- ---------------------------------------------------------------------------

-- | Render the Related block. Each anchor gets:
--   * @class="similar-link"@ — whitelist for popups.js so the default
--     footer-exclusion does not fire (content preview on hover).
--   * @data-link-icon@ / @data-link-icon-type@ — page or document icon,
--     rendered via the existing a[data-link-icon] mask-image system in
--     typography.css.
--   * For PDFs: @class="pdf-link"@ + @data-pdf-src@ + href rewritten to
--     the PDF.js viewer, matching the rest of the site. The pdfContent
--     provider in popups.js binds on @.pdf-link[data-pdf-src]@.
renderSimilarLinks :: [SimilarEntry] -> String
renderSimilarLinks entries =
    "<ul class=\"similar-links-list\">\n"
    ++ concatMap renderOne entries
    ++ "</ul>"
  where
    renderOne se
        | isPdfUrl (seUrl se) = renderPdf se
        | otherwise           = renderPage se

    renderPage se =
        "<li class=\"similar-links-item\">"
        ++ "<a class=\"similar-link\""
        ++ " href=\"" ++ escapeHtml (seUrl se) ++ "\""
        ++ " data-link-icon=\"internal\" data-link-icon-type=\"svg\">"
        ++ escapeHtml (seTitle se)
        ++ "</a></li>\n"

    renderPdf se =
        -- The PDF path becomes the @file=@ query value, so it must be
        -- percent-encoded (HTML escaping alone leaves @&@/@?@/@#@/spaces
        -- free to break the query). A @#page=N@ fragment stays a fragment
        -- of the viewer URL itself — PDF.js reads it from location.hash.
        let raw          = seUrl se
            (path, frag) = break (== '#') raw
            viewerUrl    = "/pdfjs/web/viewer.html?file="
                        ++ percentEncode path ++ escapeHtml frag
        in  "<li class=\"similar-links-item\">"
            ++ "<a class=\"similar-link pdf-link\""
            ++ " href=\"" ++ viewerUrl ++ "\""
            ++ " data-pdf-src=\"" ++ escapeHtml raw ++ "\""
            ++ " data-link-icon=\"document\" data-link-icon-type=\"svg\">"
            ++ escapeHtml (seTitle se)
            ++ "</a></li>\n"

    isPdfUrl u =
        let lower = T.toLower (T.pack u)
            (path, _) = T.break (== '#') lower
        in  ".pdf" `T.isSuffixOf` path

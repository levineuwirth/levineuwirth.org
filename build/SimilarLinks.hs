{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Similar-links field: injects a "Related" list into essay/page contexts.
--
-- @data/similar-links.json@ is produced by @tools/embed.py@ at build time
-- (stage 2 of @make build@, between the two compile passes). It is a plain
-- JSON object mapping root-relative URL paths to lists of similar pages:
--
--   { "/essays/my-essay/": [{"url": "...", "title": "...", "score": 0.87}] }
--
-- @site footer-data@ splits it into one file per page (build/FooterData.hs),
-- keeping each page's top 'maxRelated' entries without their scores, and
-- 'similarLinksField' renders the current page's.
--
-- If the file is absent (e.g. @.venv@ not set up, or first build) no page
-- has entries, and no "Related" section is rendered.
module SimilarLinks (similarLinksField) where

import qualified Data.ByteString            as BS
import qualified Data.Text                  as T
import qualified Data.Text.Encoding         as TE
import qualified Data.Aeson                 as Aeson
import           Hakyll
import           FooterData                 (footerEntries, maxRelated)

-- ---------------------------------------------------------------------------
-- JSON schema
-- ---------------------------------------------------------------------------

data SimilarEntry = SimilarEntry
    { seUrl   :: String
    , seTitle :: String
    } deriving (Show)

instance Aeson.FromJSON SimilarEntry where
    parseJSON = Aeson.withObject "SimilarEntry" $ \o ->
        SimilarEntry
            <$> o Aeson..: "url"
            <*> o Aeson..: "title"

-- ---------------------------------------------------------------------------
-- Context field
-- ---------------------------------------------------------------------------

-- | Provides @$similar-links$@, the page's Related list as HTML. Fails
-- (so the template's @$if(similar-links)$@ is false) when the page has no
-- entries in its footer file. The dependency that brings the section back
-- when entries appear is 'FooterData.footerDepsField'; the URL forms
-- @tools/embed.py@ emits are normalised when the footer files are written.
similarLinksField :: Context String
similarLinksField = field "similar-links" $ \item -> do
    entries <- footerEntries "related" item
    if null entries
        then fail "no similar links"
        else return (renderSimilarLinks (take maxRelated entries))

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

{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | External link classification.
--
--   Walks all @Link@ inlines and:
--   * Adds @class="link-external"@ to any link whose URL starts with
--     @http://@ or @https://@ and is not on the site's own domain.
--   * Adds @data-link-icon@ / @data-link-icon-type@ attributes for
--     per-domain brand icons (see 'domainIcon' for the full list).
--   * Adds @target="_blank" rel="noopener noreferrer"@ to external links.
module Filters.Links (apply) where

import           Data.Text            (Text)
import qualified Data.Text            as T
import           Text.Pandoc.Definition
import           Text.Pandoc.Walk     (walk)

-- | Apply link classification to the entire document.
--   Two passes: PDF links first (rewrites href to the viewer URL and tags
--   the anchor @pdf-link@), then general classification. The second pass
--   explicitly skips anchors the PDF pass already claimed — the viewer URL
--   is root-relative, so without that guard it would also be classified as
--   an internal page link and get double chrome.
apply :: Pandoc -> Pandoc
apply = walk classifyLink . walk classifyPdfLink

-- | Rewrite root-relative PDF links to open via the vendored PDF.js viewer.
--   Preserves the original path in @data-pdf-src@ so the popup thumbnail
--   provider can locate the corresponding @.thumb.png@ file.
--   Skips links that are already pointing at the viewer (idempotent).
--
--   Handles fragment identifiers (e.g. @/papers/foo.pdf#page=5@): the
--   fragment is stripped before the @.pdf@ suffix check and re-attached
--   after the viewer URL so PDF.js's anchor handling works.
classifyPdfLink :: Inline -> Inline
classifyPdfLink (Link (ident, classes, kvs) ils (url, title))
    | "/" `T.isPrefixOf` url
    , let (path, fragment) = T.break (== '#') url
    , ".pdf" `T.isSuffixOf` T.toLower path
    , "pdf-link" `notElem` classes =
        let viewerUrl = "/pdfjs/web/viewer.html?file="
                        <> encodeQueryValue path <> fragment
            classes'  = classes ++ ["pdf-link"]
            kvs'      = kvs ++ [("data-pdf-src", path)]
        in  Link (ident, classes', kvs') ils (viewerUrl, title)
classifyPdfLink x = x

classifyLink :: Inline -> Inline
classifyLink l@(Link (_, classes, _) _ _)
    -- Source-ref links are owned by Filters.SourceRefs: they keep the
    -- inline-code chrome of their body, must not receive an external
    -- brand icon stamp, and have their own popup provider. Leave them
    -- entirely alone.
    | "source-ref" `elem` classes = l
    -- PDF links were already rewritten to the (root-relative) viewer URL
    -- and given their own chrome by 'classifyPdfLink' in the preceding
    -- pass; without this guard they would be double-classified as
    -- internal page links.
    | "pdf-link" `elem` classes = l
classifyLink (Link (ident, classes, kvs) ils (url, title))
    | isExternal url =
        let icon     = domainIcon url
            classes' = classes ++ ["link-external"]
            kvs'     = kvs
                       ++ [("target",             "_blank")]
                       ++ [("rel",                "noopener noreferrer")]
                       ++ [("data-link-icon",      icon)]
                       ++ [("data-link-icon-type", "svg")]
        in  Link (ident, classes', kvs') ils (url, title)
    | isInternalPage url =
        let classes' = classes ++ ["link-internal"]
            kvs'     = kvs
                       ++ [("data-link-icon",      "internal")]
                       ++ [("data-link-icon-type", "svg")]
        in  Link (ident, classes', kvs') ils (url, title)
classifyLink x = x

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

-- | True if the URL is a root-relative or relative path to another page
--   (not an anchor-only link like @#section@ or @#ref-foo@).
isInternalPage :: Text -> Bool
isInternalPage url
    | T.null url                  = False
    | "#" `T.isPrefixOf` url      = False   -- anchor-only
    | "mailto:" `T.isPrefixOf` url = False
    | "http://"  `T.isPrefixOf` url = False  -- handled by isExternal
    | "https://" `T.isPrefixOf` url = False
    | otherwise                    = True

-- | True if the URL points outside the site's content host.
--
--   Only @levineuwirth.org@ and @www.levineuwirth.org@ count as the content
--   site itself. Sibling subdomains like @git.levineuwirth.org@ (Forgejo) are
--   distinct services and are classified as external so they receive their
--   brand icon, @target=_blank@, and @rel=noopener noreferrer@.
--
--   Uses strict hostname comparison rather than substring matching, so a
--   hostile lookalike like @evil-levineuwirth.org.attacker.com@ is also
--   correctly classified as external.
isExternal :: Text -> Bool
isExternal url =
    case extractHost url of
        Nothing   -> False
        Just host -> host /= siteHost && host /= "www." <> siteHost
  where
    siteHost = "levineuwirth.org"

-- | Extract the lowercased hostname from an absolute http(s) URL,
--   stripping any userinfo (@user:pass\@@) and port. Returns 'Nothing'
--   for non-http(s) URLs (relative paths, mailto:, etc.).
extractHost :: Text -> Maybe Text
extractHost url
    | Just rest <- T.stripPrefix "https://" url = Just (hostOf rest)
    | Just rest <- T.stripPrefix "http://"  url = Just (hostOf rest)
    | otherwise                                  = Nothing
  where
    hostOf rest =
        let authority = T.takeWhile (\c -> c /= '/' && c /= '?' && c /= '#') rest
            -- 'T.breakOnEnd' yields the segment after the last @\@@, or
            -- the whole authority when there is no userinfo.
            (_, hostPort) = T.breakOnEnd "@" authority
            host          = T.takeWhile (/= ':') hostPort
        in  T.toLower host

-- | Icon name for the link, matching a file in /images/link-icons/<name>.svg.
--
--   Matches on the URL's host only, never on the full URL — a path like
--   @https://example.org/why-x.com-failed@ must not get the Twitter
--   icon. URLs with no extractable host get the generic icon.
domainIcon :: Text -> Text
domainIcon url = maybe "external" iconForHost (extractHost url)

iconForHost :: Text -> Text
iconForHost host
    -- Scholarly / reference
    | m "wikipedia.org"        = "wikipedia"
    | m "arxiv.org"            = "arxiv"
    | m "doi.org"              = "doi"
    | m "worldcat.org"         = "worldcat"
    | m "orcid.org"            = "orcid"
    | m "archive.org"          = "internet-archive"
    -- Code / software
    | m "github.com"           = "github"
    | m "git.levineuwirth.org" = "forgejo"
    | m "tensorflow.org"       = "tensorflow"
    -- AI companies (consumer products share a brand icon with the lab)
    | m "anthropic.com"        = "anthropic"
    | m "claude.ai"            = "anthropic"
    | m "openai.com"           = "openai"
    | m "chatgpt.com"          = "openai"
    -- Social / media
    | m "twitter.com"          = "twitter"
    | m "x.com"                = "twitter"
    | m "reddit.com"           = "reddit"
    | m "youtube.com"          = "youtube"
    | m "youtu.be"             = "youtube"
    | m "tiktok.com"           = "tiktok"
    | m "substack.com"         = "substack"
    | m "news.ycombinator.com" = "hacker-news"
    | m "lesswrong.com"        = "lesswrong"
    -- News
    | m "nytimes.com"          = "new-york-times"
    -- Institutions
    | m "nasa.gov"             = "nasa"
    | m "apple.com"            = "apple"
    | otherwise                = "external"
  where
    -- Label-suffix match: the host is the domain itself or a subdomain
    -- of it. Never fires on a lookalike label (@notx.com@) or on text
    -- in the path or query.
    m d = host == d || ("." <> d) `T.isSuffixOf` host

-- | Percent-encode characters that would break a @?file=@ query-string value.
--   Slashes are intentionally left unencoded so root-relative paths remain
--   readable and work correctly with PDF.js's internal fetch.
encodeQueryValue :: Text -> Text
encodeQueryValue = T.concatMap enc
  where
    enc ' ' = "%20"
    enc '&' = "%26"
    enc '?' = "%3F"
    enc '+' = "%2B"
    enc '"' = "%22"
    enc c   = T.singleton c

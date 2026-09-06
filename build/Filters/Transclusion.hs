{-# LANGUAGE GHC2021 #-}
-- | Source-level transclusion preprocessor.
--
--   Rewrites block-level {{slug}} and {{slug#section}} directives to raw
--   HTML placeholders that transclude.js resolves at runtime.
--
--   A directive must be the sole content of a line (after trimming) to be
--   replaced — this prevents accidental substitution inside prose.
--
--   Code protection (honest scope): lines inside /fenced/ code blocks
--   are passed through untouched ('Filters.Wikilinks.mapOutsideFences'),
--   so fenced examples can show @{{slug}}@ literally. Indented code
--   blocks and inline code spans are NOT recognised — a full-line
--   directive inside either is still rewritten.
--
--   Examples:
--     {{my-essay}}              → full-page transclusion of /my-essay.html
--     {{essays/deep-dive}}      → /essays/deep-dive.html (full body)
--     {{my-essay#introduction}} → section "introduction" of /my-essay.html
--     {{build/}}                → /build/ (explicit directory form)
module Filters.Transclusion (preprocess) where

import Data.List (isSuffixOf, isPrefixOf, stripPrefix)
import Filters.Wikilinks (mapOutsideFences, slugUrlPath)
import qualified Utils as U

-- | Apply transclusion substitution to the raw Markdown source string,
--   skipping lines inside fenced code blocks.
preprocess :: String -> String
preprocess = mapOutsideFences processLine

processLine :: String -> String
processLine line =
    case parseDirective (U.trim line) of
        Nothing             -> line
        Just (url, secAttr) ->
            "<div class=\"transclude\" data-src=\"" ++ escAttr url ++ "\""
            ++ secAttr ++ ">" ++ noscriptFallback url secAttr ++ "</div>"

-- | No-JavaScript fallback for a transclusion placeholder.
--
--   The placeholder was emitted empty, so a reader without scripting (or
--   with a failed fetch before @transclude.js@ runs at all) got a silent
--   gap where a passage should be — the same defect F06 fixed for a
--   /failed/ transclusion, but for the case where the script never runs.
--
--   @\<noscript\>@ is inert whenever scripting is on, so this costs the
--   ordinary reader nothing and needs no cooperation from the script:
--   @transclude.js@ appends its content alongside, and the browser never
--   renders the noscript body. The link is the same destination
--   'showError' offers, including the section fragment when the directive
--   named one.
noscriptFallback :: String -> String -> String
noscriptFallback url secAttr =
    "<noscript><p class=\"transclude-noscript-note\">"
    ++ "<a href=\"" ++ href ++ "\">"
    ++ "Read this passage on its own page</a>.</p></noscript>"
  where
    -- secAttr is either "" or ` data-section="…"`; recover the section so
    -- the fallback link lands on the same heading the transclusion would
    -- have shown. Its value is already attribute-escaped, so only the URL
    -- half needs escaping here — escaping the whole would double up.
    href = case sectionOf secAttr of
        Just sec -> escAttr url ++ "#" ++ sec
        Nothing  -> escAttr url

    sectionOf s = do
        rest <- stripPrefix " data-section=\"" s
        stripSuffix "\"" rest

-- | Parse a {{slug}} or {{slug#section}} directive.
--   Returns (absolute-url, section-attribute-string) or Nothing.
--
--   The section name is HTML-escaped before being interpolated into the
--   @data-section@ attribute, so a stray @\"@, @&@, @<@, or @>@ in a
--   section name cannot break the surrounding markup.
parseDirective :: String -> Maybe (String, String)
parseDirective s = do
    inner <- stripPrefix "{{" s >>= stripSuffix "}}"
    case break (== '#') inner of
        ("", _)            -> Nothing
        (slug, "")         -> Just (slugToUrl slug, "")
        (slug, '#' : sec)
            | null sec     -> Just (slugToUrl slug, "")
            | otherwise    -> Just (slugToUrl slug,
                                    " data-section=\"" ++ escAttr sec ++ "\"")
        _                  -> Nothing

-- | Convert a slug (possibly with leading slash, possibly with path segments)
--   to a root-relative URL.
--
--   Three supported forms, in precedence order:
--
--     * a slug ending in @\/@ is a directory route and maps to itself
--       (@{{build\/}}@ → @\/build\/@) — the explicit escape hatch for any
--       page whose route is @\<slug\>\/index.html@;
--     * a slug ending in @index.html@ is the Hakyll /route/ of a
--       directory-index page written out longhand, and collapses to the
--       directory form it is served under (audit C03) — @.html@ mapping
--       to itself would otherwise publish a second spelling of a page
--       whose canonical link, sitemap entry and navigation all say
--       @\/essays\/x\/@;
--     * any other slug ending in @.html@ maps to itself (idempotent, so
--       callers can safely pass either form);
--     * a bare slug goes through 'slugUrlPath', which knows the small set
--       of top-level slugs that route to a directory index and appends
--       @.html@ to everything else. That table is shared with the
--       wikilink preprocessor so @[[Build]]@ and @{{build}}@ resolve to
--       the same existing route.
slugToUrl :: String -> String
slugToUrl slug
    | "/" `isSuffixOf` slug, "/" `isPrefixOf` slug     = slug
    | "/" `isSuffixOf` slug                            = "/" ++ slug
    | "index.html" `isSuffixOf` slug, "/" `isPrefixOf` slug
                                                       = "/" ++ slugUrlPath (drop 1 slug)
    | "index.html" `isSuffixOf` slug                   = "/" ++ slugUrlPath slug
    | ".html" `isSuffixOf` slug, "/" `isPrefixOf` slug = slug
    | ".html" `isSuffixOf` slug                        = "/" ++ slug
    | "/" `isPrefixOf` slug                            = "/" ++ slugUrlPath (drop 1 slug)
    | otherwise                                        = "/" ++ slugUrlPath slug

-- | Minimal HTML attribute-value escape.
escAttr :: String -> String
escAttr = concatMap esc
  where
    esc '&'  = "&amp;"
    esc '<'  = "&lt;"
    esc '>'  = "&gt;"
    esc '"'  = "&quot;"
    esc '\'' = "&#39;"
    esc c    = [c]

-- | Strip a suffix from a string, returning Nothing if not present.
stripSuffix :: String -> String -> Maybe String
stripSuffix suf str
    | suf `isSuffixOf` str = Just (take (length str - length suf) str)
    | otherwise             = Nothing


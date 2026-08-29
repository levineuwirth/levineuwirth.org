{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Inline SVG score fragments into the Pandoc AST.
--
-- Fenced-div syntax in Markdown:
--
-- > :::score-fragment{score-name="Main Theme, mm. 1–8" score-caption="The opening gesture."}
-- > ![](scores/main-theme.svg)
-- > :::
--
-- The filter reads the referenced SVG from disk (path resolved relative to
-- the source file's directory), replaces hardcoded black fills/strokes with
-- @currentColor@ for dark-mode compatibility, and emits a @\<figure\>@ with
-- the appropriate exhibit attributes for gallery.js TOC integration.
module Filters.Score (inlineScores) where

import           Control.Exception      (IOException, try)
import           Data.Char              (isHexDigit)
import           Data.Maybe             (listToMaybe)
import qualified Data.Text              as T
import qualified Data.Text.IO           as TIO
import           System.Directory       (doesFileExist)
import           System.FilePath        ((</>))
import           System.IO              (hPutStrLn, stderr)
import           Text.Pandoc.Definition
import           Text.Pandoc.Walk       (walkM)
import qualified Utils                  as U

-- | Walk the Pandoc AST and inline all score-fragment divs.
--   @baseDir@ is the directory of the source file; image paths in the
--   fenced-div are resolved relative to it.
inlineScores :: FilePath -> Pandoc -> IO Pandoc
inlineScores baseDir = walkM (inlineScore baseDir)

inlineScore :: FilePath -> Block -> IO Block
inlineScore baseDir (Div (_, cls, attrs) blocks)
    | "score-fragment" `elem` cls = do
        let mName    = lookup "score-name"    attrs
            mCaption = lookup "score-caption" attrs
            mPath    = findImagePath blocks
        case mPath of
            Nothing   -> return $ Div ("", cls, attrs) blocks
            Just path -> do
                let fullPath = baseDir </> T.unpack path
                exists <- doesFileExist fullPath
                if not exists
                    then do
                        hPutStrLn stderr $
                            "[Score] missing SVG: " ++ fullPath
                            ++ " (referenced from a score-fragment in " ++ baseDir ++ ")"
                        return (errorBlock mName ("Missing score: " <> path))
                    else do
                        result <- try (TIO.readFile fullPath) :: IO (Either IOException T.Text)
                        case result of
                            Left e -> do
                                hPutStrLn stderr $
                                    "[Score] read error on " ++ fullPath ++ ": " ++ show e
                                return (errorBlock mName ("Could not read score: " <> path))
                            Right svgRaw -> do
                                let html = buildHtml mName mCaption (processColors svgRaw)
                                return $ RawBlock (Format "html") html
inlineScore _ block = return block

-- | Render an inline error block in place of a missing or unreadable score.
--   Mirrors the convention in 'Filters.Viz.errorBlock' so build failures are
--   visible to the author without aborting the entire site build.
errorBlock :: Maybe T.Text -> T.Text -> Block
errorBlock mName message =
    RawBlock (Format "html") $ T.concat
        [ "<figure class=\"score-fragment score-fragment--error\""
        , maybe "" (\n -> " data-exhibit-name=\"" <> escHtml n <> "\"") mName
        , ">"
        , "<div class=\"score-fragment-error\">"
        , escHtml message
        , "</div>"
        , "</figure>"
        ]

-- | Extract the image src from the first Para that contains an Image inline.
findImagePath :: [Block] -> Maybe T.Text
findImagePath blocks = listToMaybe
    [ src
    | Para inlines       <- blocks
    , Image _ _ (src, _) <- inlines
    ]

-- | Replace hardcoded black fill/stroke values with @currentColor@ so the
--   SVG inherits the CSS @color@ property in both light and dark modes.
--
--   Quoted attribute forms (@fill="#000"@) are self-delimiting — the
--   closing quote bounds the match — so plain 'T.replace' is safe for
--   them. Unquoted style-property forms (@fill:#000@) are not: naive
--   replacement would also fire on the prefix of a longer hex colour
--   (@fill:#000080@ → @fill:currentColor80@, invalid CSS). Those go
--   through 'replaceHexColor', which rewrites a match only when it is
--   not followed by another hex digit; the boundary check also makes
--   the 3-digit/6-digit application order irrelevant.
processColors :: T.Text -> T.Text
processColors
    -- 3-digit hex and keyword patterns
    = T.replace "fill=\"#000\""       "fill=\"currentColor\""
    . T.replace "fill=\"black\""      "fill=\"currentColor\""
    . T.replace "stroke=\"#000\""    "stroke=\"currentColor\""
    . T.replace "stroke=\"black\""   "stroke=\"currentColor\""
    . replaceHexColor "fill:#000"    "fill:currentColor"
    . T.replace "fill:black"         "fill:currentColor"
    . replaceHexColor "stroke:#000" "stroke:currentColor"
    . T.replace "stroke:black"      "stroke:currentColor"
    -- 6-digit hex patterns (applied first — bottom of the chain)
    . T.replace "fill=\"#000000\""    "fill=\"currentColor\""
    . T.replace "stroke=\"#000000\"" "stroke=\"currentColor\""
    . replaceHexColor "fill:#000000" "fill:currentColor"
    . replaceHexColor "stroke:#000000" "stroke:currentColor"

-- | 'T.replace' restricted to hex-boundary-terminated matches: an
--   occurrence of @needle@ is rewritten only when the character after
--   it is not another hex digit, so @fill:#000@ never fires inside the
--   longer colours @fill:#0008@, @fill:#000080@, or @fill:#00000080@.
replaceHexColor :: T.Text -> T.Text -> T.Text -> T.Text
replaceHexColor needle replacement = go
  where
    go t =
        let (pre, rest) = T.breakOn needle t
        in  if T.null rest
                then pre
                else
                    let after = T.drop (T.length needle) rest
                    in  case T.uncons after of
                            Just (c, _) | isHexDigit c ->
                                pre <> needle <> go after
                            _ -> pre <> replacement <> go after

buildHtml :: Maybe T.Text -> Maybe T.Text -> T.Text -> T.Text
buildHtml mName mCaption svgContent = T.concat
    [ "<figure class=\"score-fragment exhibit\""
    , maybe "" (\n -> " data-exhibit-name=\"" <> escHtml n <> "\"") mName
    , " data-exhibit-type=\"score\">"
    , "<div class=\"score-fragment-inner\">"
    , svgContent
    , "</div>"
    , maybe "" (\c -> "<figcaption class=\"score-caption\">" <> escHtml c <> "</figcaption>") mCaption
    , "</figure>"
    ]

escHtml :: T.Text -> T.Text
escHtml = U.escapeHtmlText

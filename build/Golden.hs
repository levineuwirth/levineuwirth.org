{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | @site render-fixture <file.md>@: one Markdown file through the essay
--   pipeline, printed to stdout, for the golden-page tests
--   (tests/test_golden.py, fixtures in tests/golden/).
--
--   The filters are the part of the site with the most behaviour and, until
--   these tests, none of their own: a page either built or it did not. A
--   golden test needs a page whose source never changes, and a fixture in
--   content/ would be published, so this renders the file outside Hakyll
--   instead. It shares every step that matters with 'Compilers.essayCompiler'
--   — 'preprocessSource', the Hakyll reader options, heading normalisation,
--   'Compilers.transformDocument', the writer options and 'Compilers.buildTOC'
--   — and skips only what needs a running build: templates, contexts, and the
--   dependency tracking.
--
--   Relative paths (the bibliography, the CSL style, files beside the
--   fixture) resolve from the working directory, so run it from the
--   repository root, as the test does.
module Golden (renderFixture) where

import qualified Data.ByteString.Char8 as BS
import qualified Data.Text             as T
import qualified Data.Text.IO          as TIO
import qualified Data.Yaml             as Yaml
import           Data.Maybe            (fromMaybe)
import           Hakyll                (Metadata, lookupString, lookupStringList)
import           System.Exit           (exitFailure)
import           System.FilePath       (takeDirectory)
import           System.IO             (hPutStrLn, stderr)
import           Text.Pandoc           (readMarkdown, runPure, writeHtml5String)

import           Compilers             (readerOpts, writerOpts, transformDocument,
                                        buildTOC, parseBool)
import           Filters               (preprocessSource)
import qualified Filters.Headings      as Headings

-- | Render one fixture: the body, then the table of contents, the
--   bibliography and the further-reading list, each under a marker line.
renderFixture :: FilePath -> IO ()
renderFixture path = do
    (meta, body) <- splitFrontMatter path <$> readFile path >>= either die return
    let frKeys        = map T.pack (fromMaybe [] (lookupStringList "further-reading" meta))
        bibPath       = T.pack (fromMaybe "data/bibliography.bib" (lookupString "bibliography" meta))
        numberFigures = fromMaybe False (lookupString "figure-numbering" meta >>= parseBool)
    parsed <- either (die . show) return $
        runPure (readMarkdown readerOpts (T.pack (preprocessSource body)))
    (doc, bibHtml, furtherHtml) <-
        transformDocument frKeys bibPath numberFigures (takeDirectory path)
                          (Headings.normalizeLevels parsed)
    html <- either (die . show) return $ runPure (writeHtml5String writerOpts doc)
    mapM_ (\(name, part) -> TIO.putStrLn ("<!-- render-fixture: " <> name <> " -->")
                         >> TIO.putStrLn part)
        [ ("body",            html)
        , ("toc",             T.pack (buildTOC doc))
        , ("bibliography",    bibHtml)
        , ("further-reading", furtherHtml)
        ]
  where
    die msg = hPutStrLn stderr ("render-fixture: " ++ path ++ ": " ++ msg) >> exitFailure

-- | Hakyll's page split: a leading @---@ line opens the YAML front matter,
--   and the next @---@ or @...@ line closes it.
splitFrontMatter :: FilePath -> String -> Either String (Metadata, String)
splitFrontMatter _ src = case lines src of
    (open : rest) | isFence open ->
        case break isClose rest of
            (yamlLines, _ : bodyLines) ->
                case Yaml.decodeEither' (BS.pack (unlines yamlLines)) of
                    Left err   -> Left (Yaml.prettyPrintParseException err)
                    Right meta -> Right (meta, unlines bodyLines)
            _ -> Left "front matter is never closed"
    _ -> Right (mempty, src)
  where
    isFence l = trimEnd l == "---"
    isClose l = trimEnd l `elem` ["---", "..."]
    trimEnd   = reverse . dropWhile (`elem` (" \t\r" :: String)) . reverse

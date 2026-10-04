module Main where

import Control.Monad         (when)
import Data.Time.Clock.POSIX (getPOSIXTime)
import System.Directory      (createDirectoryIfMissing)
import System.Environment    (getArgs)
import Hakyll                (hakyllWith)
import Golden                (renderFixture)
import Site                  (rules, siteConfigurationFor)
import Drafts                (currentUnpublished, scanUnpublished, unpublishedSummary,
                              withoutUnpublished)
import BibExtras             (BibExtra (..), parseBibExtras)
import Marks                 (epistemicVocabulary)
import Patterns              (reservedSectionDirs)
import qualified Data.Aeson  as Aeson
import qualified Data.ByteString.Lazy.Char8 as LBS
import qualified Data.Map.Strict as Map
import Data.List             (intercalate)
import Data.Maybe            (fromMaybe)
import Utils                 (isDevBuild, outputDirFor)
import FooterData            (writeFooterData)

-- | Stamp the start of this build into @data/build-stamp.txt@ before
-- Hakyll scans the provider directory. The file therefore always exists
-- and always differs from the previous run. The telemetry pages
-- (@/build/@, @/stats/@) @load@ it as a dependency so Hakyll recompiles
-- them on every build instead of serving a stale cached copy when no
-- tracked content changed. See build/Stats.hs and build/Site.hs.
writeBuildStamp :: IO ()
writeBuildStamp = do
    createDirectoryIfMissing True "data"
    t <- getPOSIXTime
    writeFile "data/build-stamp.txt" (show t ++ "\n")

-- | 'siteConfigurationFor' (not 'Hakyll.defaultConfiguration') is the
-- publication boundary: it extends Hakyll's @ignoreFile@ so that private
-- notes, key material, and editor/interpreter junk never become
-- identifiers, and therefore can never be routed into @_site/@. See
-- build/Site.hs. Pages flagged @draft: true@ are withheld after the rules
-- run instead ('withoutUnpublished', build/Drafts.hs): @ignoreFile@ sees
-- only bare file names, and a draft is known by its path.
--
-- Commands Hakyll does not see: @site render-fixture <file.md>@ renders
-- a test fixture through the essay pipeline and writes nothing
-- (build/Golden.hs); @site footer-data@ splits the backlinks and
-- similar-links maps into per-page files between the two compile passes
-- (build/FooterData.hs); @site list-unpublished@ prints what a production
-- build withholds for @draft: true@; @site bib-extras FILE@ prints what the
-- .bib scanner (build/BibExtras.hs) reads from a file, one key per line;
-- @site epistemic-vocab@ prints the epistemic fields' vocabularies as JSON
-- (build/Marks.hs), for the tools and tests that must agree with them;
-- @site reserved-sections@ prints the content directories a page collection
-- may not take (build/Patterns.hs), one per line.
main :: IO ()
main = do
    args <- getArgs
    case args of
        ["render-fixture", path] -> renderFixture path
        ["list-unpublished"] -> scanUnpublished "content" >>= mapM_ putStrLn . unpublishedSummary
        ["epistemic-vocab"] -> LBS.putStrLn (Aeson.encode (Map.fromList epistemicVocabulary))
        ["reserved-sections"] -> mapM_ putStrLn reservedSectionDirs
        ["bib-extras", path] -> do
            extras <- parseBibExtras path
            mapM_ (\(k, e) -> putStrLn (intercalate "\t"
                      [k, fromMaybe "" (bibFile e), intercalate "," (bibKeywords e)]))
                  (Map.toList extras)
        ["list-unpublished", root] -> scanUnpublished root >>= mapM_ putStrLn . unpublishedSummary
        ["footer-data"] -> do
            dev <- isDevBuild
            when dev $ fail "footer-data: production builds only (a dev build's backlinks include drafts)"
            writeFooterData (outputDirFor False)
        _ -> do
            writeBuildStamp
            dev <- isDevBuild
            hakyllWith (siteConfigurationFor dev) (withoutUnpublished currentUnpublished rules)

module Main where

import Control.Monad         (when)
import Data.Time.Clock.POSIX (getPOSIXTime)
import System.Directory      (createDirectoryIfMissing)
import System.Environment    (getArgs)
import Hakyll                (hakyllWith)
import Golden                (renderFixture)
import Site                  (rules, siteConfigurationFor)
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
-- build/Site.hs.
--
-- Two commands Hakyll does not see: @site render-fixture <file.md>@ renders
-- a test fixture through the essay pipeline and writes nothing
-- (build/Golden.hs); @site footer-data@ splits the backlinks and
-- similar-links maps into per-page files between the two compile passes
-- (build/FooterData.hs).
main :: IO ()
main = do
    args <- getArgs
    case args of
        ["render-fixture", path] -> renderFixture path
        ["footer-data"] -> do
            dev <- isDevBuild
            when dev $ fail "footer-data: production builds only (a dev build's backlinks include drafts)"
            writeFooterData (outputDirFor False)
        _ -> do
            writeBuildStamp
            dev <- isDevBuild
            hakyllWith (siteConfigurationFor dev) rules

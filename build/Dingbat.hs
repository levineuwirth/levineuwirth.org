{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}

-- | Section-break ornament selection.
--
-- Every page exposes a @$dingbat$@ template variable naming the ornament to
-- use in place of the standard @<hr>@. The template renders this as
-- @data-dingbat="..."@ on @<body>@; CSS attribute selectors then swap the
-- @hr::after@ glyph.
--
-- Resolution order:
--
--   1. @dingbat:@ frontmatter key on the page (must be in 'knownDingbats').
--   2. Section default derived from the item's route ('sectionDefault').
--   3. Fallback ('fallbackDingbat').
--
-- Best practice: set @dingbat:@ explicitly in frontmatter. The section
-- defaults are a safety net, not a substitute.
--
-- Adding a new ornament:
--
--   1. Add its name to 'knownDingbats' ("Config").
--   2. Optionally make it a section's default in site.yaml.
--   3. Add a matching @body[data-dingbat="…"]@ rule in typography.css.
module Dingbat
    ( dingbatField
    , knownDingbats
    ) where

import Data.Maybe          (fromMaybe)
import Hakyll
import Config              (SiteConfig, knownDingbats, loadConfig)
import Sections            (Section (..), sectionOfRoute)

-- | Last-resort default when neither frontmatter nor section rule applies.
fallbackDingbat :: String
fallbackDingbat = "asterism"

-- | The section's default ornament (site.yaml); a route in no section,
--   or in one without a default, uses 'fallbackDingbat'.
sectionDefault :: SiteConfig -> String -> String
sectionDefault cfg r = fromMaybe fallbackDingbat (sectionOfRoute cfg r >>= sectionDingbat)

-- | @$dingbat$@: name of the ornament to use on this page.
dingbatField :: Context a
dingbatField = field "dingbat" $ \item -> do
    cfg  <- loadConfig
    meta <- getMetadata (itemIdentifier item)
    r    <- fromMaybe "" <$> getRoute (itemIdentifier item)
    let sectionD = sectionDefault cfg r
    case lookupString "dingbat" meta of
        Nothing -> return sectionD
        Just name
            | name `elem` knownDingbats -> return name
            | otherwise -> do
                let ident = toFilePath (itemIdentifier item)
                unsafeCompiler $ putStrLn $
                    "[Dingbat] " ++ ident ++ ": unknown dingbat \""
                    ++ name ++ "\" — using \"" ++ sectionD ++ "\""
                return sectionD

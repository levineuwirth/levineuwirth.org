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
--   1. Add its name to 'knownDingbats'.
--   2. Optionally assign a section default in 'sectionDefault'.
--   3. Add a matching @body[data-dingbat="…"]@ rule in typography.css.
module Dingbat
    ( dingbatField
    , knownDingbats
    ) where

import Data.List           (isPrefixOf)
import Data.Maybe          (fromMaybe)
import Hakyll

-- | Curated palette. Extend here when adding a new ornament.
knownDingbats :: [String]
knownDingbats =
    [ "asterism"    -- ⁂ typographic asterism (neutral fallback)
    , "asterisks"   -- * * * spaced asterisks (classic scene break)
    , "fleuron"     -- Aldine leaf (literary essays)
    , "trefoil"     -- three-lobed ornament (poetry)
    , "lozenge"     -- diamond/rhombus (blog)
    , "clef"        -- musical ornament (music)
    , "memento"     -- mourning ornament (memento-mori)
    , "tech"        -- tech ornament
    , "ai"          -- AI ornament (the cute robot)
    ]

-- | Last-resort default when neither frontmatter nor section rule applies.
fallbackDingbat :: String
fallbackDingbat = "asterism"

-- | Section defaults matched against the item's route prefix.
--   First matching prefix wins. Unmatched routes use 'fallbackDingbat'.
sectionDefault :: String -> String
sectionDefault r
    | "essays/"       `isPrefixOf` r = "fleuron"
    | "blog/"         `isPrefixOf` r = "lozenge"
    | "poetry/"       `isPrefixOf` r = "trefoil"
    | "fiction/"      `isPrefixOf` r = "asterisks"
    | "music/"        `isPrefixOf` r = "clef"
    | "memento-mori/" `isPrefixOf` r = "memento"
    | otherwise                       = fallbackDingbat

-- | @$dingbat$@: name of the ornament to use on this page.
dingbatField :: Context a
dingbatField = field "dingbat" $ \item -> do
    meta <- getMetadata (itemIdentifier item)
    r    <- fromMaybe "" <$> getRoute (itemIdentifier item)
    let sectionD = sectionDefault r
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

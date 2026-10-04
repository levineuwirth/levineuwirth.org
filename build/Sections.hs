{-# LANGUAGE GHC2021 #-}
-- | The site's content sections, keyed by the route their pages take:
--   each one's label on the New page (@$item-kind$@, "Contexts") and its
--   default ornament (@$dingbat$@, "Dingbat"). The two used to dispatch on
--   their own copies of these route prefixes.
module Sections
    ( Section (..)
    , sectionOfRoute
    ) where

import Data.List (find, isPrefixOf)

data Section = Section
    { sectionDir     :: String        -- ^ its pages: @<dir>/…@, or @<dir>.html@
    , sectionKind    :: String        -- ^ @$item-kind$@
    , sectionDingbat :: Maybe String  -- ^ default ornament; 'Nothing' takes the fallback
    }

sections :: [Section]
sections =
    [ Section "essays"       "Essay"       (Just "fleuron")
    , Section "blog"         "Post"        (Just "lozenge")
    , Section "poetry"       "Poem"        (Just "trefoil")
    , Section "fiction"      "Fiction"     (Just "asterisks")
    , Section "music"        "Composition" (Just "clef")
    , Section "photography"  "Photo"       Nothing
    , Section "memento-mori" "Page"        (Just "memento")
    ]

-- | The section a route belongs to. A section whose one page is routed
--   beside its directory counts too: memento-mori's is @memento-mori.html@,
--   and matching only @memento-mori/@ gave it the fallback ornament
--   instead of its own until 2026-10-04.
sectionOfRoute :: FilePath -> Maybe Section
sectionOfRoute r = find owns sections
  where
    owns s = (sectionDir s ++ "/") `isPrefixOf` r || r == sectionDir s ++ ".html"

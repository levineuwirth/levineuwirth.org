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
    { sectionDir     :: String        -- ^ its pages are routed under @<dir>/@
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

-- | The section a route belongs to.
sectionOfRoute :: FilePath -> Maybe Section
sectionOfRoute r = find (\s -> (sectionDir s ++ "/") `isPrefixOf` r) sections

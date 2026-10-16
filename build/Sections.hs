{-# LANGUAGE GHC2021 #-}
-- | The site's taxonomy: its content sections and portals (site.yaml,
--   "Config") and the lists derived from them, which used to be kept by
--   hand in five modules and two templates.
--
--   * 'sectionOfRoute': a page's section, for its label on the New page
--     (@$item-kind$@, "Contexts") and its default ornament ("Dingbat").
--   * 'reservedSectionDirs': directories under @content/@ that a generic
--     page collection may not take ("Patterns", @site shared-rules@).
--   * 'sectionOwnedTopLevelTags': tags that may not have a tag page,
--     because a section or a generated page owns that URL ("Tags").
--   * 'directoryRouteSlugs': bare wikilink slugs whose page is a
--     directory index ("Filters.Wikilinks").
module Sections
    ( Section (..)
    , sectionOfRoute
    , reservedSectionDirs
    , sectionOwnedTopLevelTags
    , directoryRouteSlugs
    , generatedIndexes
    ) where

import Data.List (find, isPrefixOf, nub, sort)
import Config    (SiteConfig (..), Section (..), Portal (..))

-- | The section a route belongs to. A section whose one page is routed
--   beside its directory counts too: memento-mori's is @memento-mori.html@,
--   and matching only @memento-mori/@ gave it the fallback ornament
--   instead of its own until 2026-10-04.
sectionOfRoute :: SiteConfig -> FilePath -> Maybe Section
sectionOfRoute cfg r = find owns (siteSections cfg)
  where
    owns s = (sectionDir s ++ "/") `isPrefixOf` r || r == sectionDir s ++ ".html"

-- | The pages the engine generates at @<name>/index.html@.
--   @tests/test_wikilink_routes.py@ checks this against the routes in
--   @build/@.
generatedIndexes :: [String]
generatedIndexes = ["archive", "bibliography", "build", "stats"]

-- | Generated URL namespaces without an index of their own: an author's
--   page is @/authors/<slug>/@.
generatedNamespaces :: [String]
generatedNamespaces = ["authors"]

-- | Directories under @content/@ the engine reads for itself: the tag and
--   bibliography sidecars, drafts, and per-page scripts.
engineContentDirs :: [String]
engineContentDirs = ["bibliography-meta", "drafts", "scripts", "tag-meta"]

-- | The directories of the one-off pages under @content/@, and those whose
--   routes are a directory (@/cv/projects/@). A4's standalone-page table
--   replaces both lists.
standaloneDirs, standaloneNamespaces :: [String]
standaloneDirs       = ["cv", "me"]
standaloneNamespaces = ["cv"]

landings :: SiteConfig -> [String]
landings cfg = [sectionDir s | s <- siteSections cfg, sectionLanding s]

-- | The directories under @content/@ that belong to a section, a one-off
--   page or the engine, never to a generic page collection.
--   tools/import-content.py refuses a page collection by one of these
--   names, reading this list through @site shared-rules@.
reservedSectionDirs :: SiteConfig -> [String]
reservedSectionDirs cfg = sort . nub $
    engineContentDirs ++ map sectionDir (siteSections cfg) ++ standaloneDirs

-- | Top-level tags that must NOT get a tag page, because a section landing
--   or a generated page already owns @<tag>/index.html@. The build refuses
--   two items on one route ("RouteCheck"), so an essay tagged e.g. @music@
--   would otherwise stop it by claiming @music/index.html@. The list holds
--   every such namespace, not just the tags in use: @photography@ (every
--   photo's @tags:@ list begins with it, per the section convention) plus
--   the other section landings and generated namespaces.
--
--   Sub-tags (@photography/landscape@, @photography/film@, …) are
--   unaffected; they keep their tag pages because no section landing
--   claims those URLs.
sectionOwnedTopLevelTags :: SiteConfig -> [String]
sectionOwnedTopLevelTags cfg = nub $
    landings cfg ++ standaloneNamespaces ++ generatedIndexes ++ generatedNamespaces

-- | The bare wikilink slugs whose page is a directory index: the section
--   landings, the generated indexes and the portal tags, whose tag pages
--   are directories too. Source-level preprocessors resolve a slug without
--   Hakyll's route table, so a slug missing here links to @<slug>.html@,
--   a page that does not exist (the @/build.html@ 404 that motivated the
--   list; @[[Essays]]@ went to @/essays.html@ the same way).
directoryRouteSlugs :: SiteConfig -> [String]
directoryRouteSlugs cfg = nub $
    landings cfg ++ generatedIndexes ++ map portalTag (sitePortals cfg)

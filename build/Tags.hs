{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Hierarchical tag system.
--
--   Tags are slash-separated strings in YAML frontmatter:
--     tags: [research/mathematics, nonfiction/essays, typography]
--
--   "research/mathematics" expands to ["research", "research/mathematics"]
--   so /research/ aggregates everything tagged with any research/* sub-tag.
--
--   Pages live at /<tag>/index.html — no /tags/ namespace:
--     research              → /research/
--     research/mathematics  → /research/mathematics/
--     typography            → /typography/
--
--   Optional sidecar files at @content/tag-meta/<tag-path>.md@ supply
--   a per-tag @tooltip:@ (frontmatter) and prose intro (body). When
--   a sidecar exists, the tag page exposes @$portal-tooltip$@ and
--   @$portal-intro$@; when it is absent, both fields are noResult
--   and the corresponding @$if$@ blocks render nothing.
module Tags
    ( buildAllTags
    , applyTagRules
    , tagPaginationThreshold
    , tagPageSize
    , sidecarIdentifier
    , portalIntroField
    , portalTooltipField
    , seeAlsoContext
    ) where

import Data.Char  (isSpace)
import Data.List  (intercalate, isPrefixOf, nub, sort, sortBy)
import Data.Maybe (fromMaybe, isNothing, maybeToList)
import Data.Ord   (comparing)
import Data.Set   (Set)
import qualified Data.Set as Set
import Data.Time.Clock  (UTCTime)
import Data.Time.Format (defaultTimeLocale, parseTimeM)
import Hakyll
import Patterns   (tagIndexable)
import Contexts   (Revision (..), abstractField, contentKindField,
                   getRevisions, recentFirstByDisplay, revisionDateFields,
                   siteCtx, tagLinksFieldExcludingScope)


-- ---------------------------------------------------------------------------
-- Pagination policy
-- ---------------------------------------------------------------------------

-- | Maximum number of items for which a tag index ships its full list and
--   relies purely on the client-side 25/50/100/All toggle (matching
--   @\/new.html@). Tags above this threshold fall back to server-side
--   pagination at 'tagPageSize' per page; the count toggle then operates
--   within the current page only.
tagPaginationThreshold :: Int
tagPaginationThreshold = 150

-- | Page size used for server-side pagination on tag pages that exceed
--   'tagPaginationThreshold'.
tagPageSize :: Int
tagPageSize = 100


-- ---------------------------------------------------------------------------
-- Hierarchy expansion
-- ---------------------------------------------------------------------------

wordsBy :: (Char -> Bool) -> String -> [String]
wordsBy p s = case dropWhile p s of
    ""  -> []
    s'  -> w : wordsBy p rest
      where (w, rest) = break p s'

-- | "research/mathematics" → ["research", "research/mathematics"]
--   "a/b/c"                → ["a", "a/b", "a/b/c"]
--   "typography"           → ["typography"]
expandTag :: String -> [String]
expandTag t =
    let segs = wordsBy (== '/') t
    in  [ intercalate "/" (take n segs) | n <- [1 .. length segs] ]

-- | Top-level tags that own a section URL outside the tag system, and
--   therefore must NOT be created as tag pages — doing so would
--   collide with a section landing route. Hakyll does not error on
--   duplicate routes (one item silently overwrites the other), so an
--   essay tagged e.g. @music@ would otherwise clobber
--   @music/index.html@. The set therefore lists every namespace that
--   owns a @<name>/index.html@ route, not just the tags currently in
--   use: @photography@ (every photo's @tags:@ list begins with it, per
--   the section convention) plus the other section landings and
--   generated index namespaces.
--
--   Sub-tags (@photography/landscape@, @photography/film@, …) are
--   unaffected; they keep their tag pages because no section landing
--   claims those URLs.
sectionOwnedTopLevelTags :: [String]
sectionOwnedTopLevelTags =
    [ "photography", "poetry", "fiction", "music", "essays", "blog"
    , "cv", "archive", "authors", "bibliography"
    ]

-- | All expanded tags for an item (reads the "tags" metadata field).
--   Filters out any 'sectionOwnedTopLevelTags' to prevent route
--   collisions with section landings.
getExpandedTags :: MonadMetadata m => Identifier -> m [String]
getExpandedTags ident =
    filter (`notElem` sectionOwnedTopLevelTags) . nub . concatMap expandTag
        <$> getTags ident


-- ---------------------------------------------------------------------------
-- Identifiers and URLs
-- ---------------------------------------------------------------------------

tagFilePath :: String -> FilePath
tagFilePath tag = tag ++ "/index.html"

tagIdentifier :: String -> Identifier
tagIdentifier = fromFilePath . tagFilePath

-- | Identifier of the optional sidecar for a given tag.
--   "nonfiction"           → content/tag-meta/nonfiction.md
--   "nonfiction/philosophy" → content/tag-meta/nonfiction/philosophy.md
sidecarIdentifier :: String -> Identifier
sidecarIdentifier tag = fromFilePath ("content/tag-meta/" ++ tag ++ ".md")


-- ---------------------------------------------------------------------------
-- Building the Tags index
-- ---------------------------------------------------------------------------

-- | Scan all essays and blog posts and build the Tags index.
buildAllTags :: Rules Tags
buildAllTags =
    buildTagsWith getExpandedTags tagIndexable tagIdentifier


-- ---------------------------------------------------------------------------
-- Sidecar fields
-- ---------------------------------------------------------------------------

-- | Field exposing a sidecar's rendered HTML body as @$portal-intro$@.
--   Fails with 'noResult' when the sidecar body is empty or whitespace-only,
--   so @$if(portal-intro)$@ is false and the render site emits nothing.
--
--   Takes a function that yields the sidecar identifier from the current
--   item — this lets tag pages bind the sidecar statically at rule time
--   (@const sidecarId@) while the home-page portal listField derives it
--   per-item from the item body.
portalIntroField :: (Item a -> Identifier) -> Context a
portalIntroField getSidecarId = field "portal-intro" $ \item -> do
    let sidecarId = getSidecarId item
    html <- itemBody <$> loadSnapshot sidecarId "body"
    if all isSpace html
        then noResult "sidecar body is empty"
        else return html

-- | Field exposing a sidecar's @tooltip:@ frontmatter value as
--   @$portal-tooltip$@. Fails with 'noResult' when the key is absent
--   or the value is empty / whitespace-only. Accepts a per-item
--   identifier resolver for the same reason as 'portalIntroField'.
portalTooltipField :: (Item a -> Identifier) -> Context a
portalTooltipField getSidecarId = field "portal-tooltip" $ \item -> do
    let sidecarId = getSidecarId item
    meta <- getMetadata sidecarId
    case fmap trim (lookupString "tooltip" meta) of
        Just t | not (null t) -> return t
        _                     -> noResult "no tooltip"

-- ---------------------------------------------------------------------------
-- See Also: parent / sibling / child computation
-- ---------------------------------------------------------------------------

-- | Direct parent of a tag path. @Nothing@ for top-level tags (portals).
--   "nonfiction/philosophy" → Just "nonfiction"
--   "nonfiction"            → Nothing
--   "a/b/c"                 → Just "a/b"
parentOf :: String -> Maybe String
parentOf t = case wordsBy (== '/') t of
    []   -> Nothing
    [_]  -> Nothing
    segs -> Just (intercalate "/" (init segs))   -- 'init' safe: 2+ segments

-- | Number of @/@ characters in a tag path (i.e., depth - 1).
slashCount :: String -> Int
slashCount = length . filter (== '/')

-- | Parent / siblings / children of a scope tag, each filtered to tags that
--   appear in 'tagsMap' (i.e., have at least one item). Parent is returned
--   unconditionally — if it isn't in @tagsMap@ the See Also still links it,
--   since a parent with no direct items but some descendant items is still
--   a navigable aggregation page.
--
--   Sibling portals (scope is top-level) render in @portalOrder@. Sibling
--   subcategories (scope has a parent) render alphabetically. Children
--   always render alphabetically.
seeAlsoGroups :: [String]              -- ^ canonical portal tag order
              -> Tags                   -- ^ all tags for has-items filter
              -> String                 -- ^ current scope
              -> (Maybe String, [String], [String])
seeAlsoGroups portalOrder tags scope =
    let tKeys = map fst (tagsMap tags)
        mParent = parentOf scope

        sibs = case mParent of
            Nothing ->
                -- Scope is a portal. Siblings: other portals in tagsMap,
                -- emitted in portalOrder.
                [ p | p <- portalOrder, p /= scope, p `elem` tKeys ]
            Just parent ->
                -- Scope is a subcategory. Siblings: other direct children
                -- of the parent, alphabetical.
                sort [ s | s <- tKeys
                         , parentOf s == Just parent
                         , s /= scope
                         ]

        kids = sort
            [ c | c <- tKeys
                , (scope ++ "/") `isPrefixOf` c
                , slashCount c == slashCount scope + 1
                ]
    in (mParent, sibs, kids)


-- ---------------------------------------------------------------------------
-- See Also: rendering into a Context
-- ---------------------------------------------------------------------------

-- | Display name for a tag path. Portals get their capitalized form from
--   @portalPairs@ (e.g., "Research"); subcategories display their raw tag
--   path (e.g., "nonfiction/philosophy").
displayNameFor :: [(String, String)] -> String -> String
displayNameFor portalPairs t =
    fromMaybe t (lookup t (map (\(d, tg) -> (tg, d)) portalPairs))

-- | Item-level context for See Also entries. Body is a tag path string.
seeAlsoItemCtx :: [(String, String)] -> Context String
seeAlsoItemCtx portalPairs =
       field "see-also-name" (\i -> return (displayNameFor portalPairs (itemBody i)))
    <> field "see-also-url"  (\i -> return $ "/" ++ itemBody i ++ "/")
    <> portalTooltipField (sidecarIdentifier . itemBody)

-- | Full See Also context contribution for a scope: three listFields
--   (@see-also-parent@ at most one entry, @see-also-siblings@,
--   @see-also-children@) and a @has-see-also@ gate that fails when all
--   three are empty so the template's @$if(has-see-also)$@ suppresses
--   the entire @<nav>@ wrapper.
seeAlsoContext :: [(String, String)] -> Tags -> String -> Context String
seeAlsoContext portalPairs tags scope =
       listField "see-also-parent"   itemCtx (return (toItems (maybeToList mParent)))
    <> listField "see-also-siblings" itemCtx (return (toItems sibs))
    <> listField "see-also-children" itemCtx (return (toItems kids))
    <> field     "has-see-also" (\_ ->
          if isNothing mParent && null sibs && null kids
              then noResult "no see-also entries"
              else return "true")
  where
    (mParent, sibs, kids) = seeAlsoGroups (map snd portalPairs) tags scope
    itemCtx = seeAlsoItemCtx portalPairs
    toItems = map (Item (fromFilePath ""))


-- | Context contribution for the current tag's sidecar, if one exists,
--   and eager registration of the snapshot dependency.
--
--   When a sidecar exists, the body snapshot is loaded unconditionally
--   (and discarded) so Hakyll's dependency tracker sees the edge
--   /tag page → sidecar body/ on every compile — even when the
--   rendered @$if(portal-intro)$@ gate is false because the body is
--   empty. Without this, the first build after populating a previously
--   empty sidecar would not re-render the tag page (the lazy field
--   load inside 'portalIntroField' never fires while the gate is
--   false, so the dep is never established).
--
--   Tags with no sidecar take the @mempty@ branch and register no
--   dependency, which is correct — there is nothing to depend on.
sidecarContext :: Set Identifier -> String -> Compiler (Context String)
sidecarContext sidecarSet tag
    | sidecarId `Set.member` sidecarSet = do
        _ <- loadSnapshot sidecarId "body" :: Compiler (Item String)
        return ( portalIntroField   (const sidecarId)
              <> portalTooltipField (const sidecarId))
    | otherwise = return mempty
  where
    sidecarId = sidecarIdentifier tag


-- ---------------------------------------------------------------------------
-- Tag index page rules
-- ---------------------------------------------------------------------------

-- | Item-level context used inside @$for(items)$@ on tag index pages.
--   Provides the fields consumed by @templates/partials/item-card.html@
--   (@$item-kind$@, @$date-iso$@, @$date-created$@, @$abstract$@,
--   @$item-tags$@) with tag-ribbon suppression scoped to the current tag.
--
--   Composes 'siteCtx' (not bare 'defaultContext') so per-item fields
--   the card partial gates on — notably @$has-monogram$@ — fire here
--   the same way they do on /new.html and the library.
tagItemCtx :: String -> Context String
tagItemCtx scope =
    contentKindField
    <> dateField "date-created"  "%-d %B %Y"
    <> dateField "date"          "%-d %B %Y"
    <> revisionDateFields
    <> tagLinksFieldExcludingScope "item-tags" scope
    <> abstractField
    <> siteCtx

-- | Page identifier for a tag index page.
--   Page 1 → <tag>/index.html
--   Page N → <tag>/page/N/index.html
tagPageId :: String -> PageNumber -> Identifier
tagPageId tag 1 = fromFilePath $ tag ++ "/index.html"
tagPageId tag n = fromFilePath $ tag ++ "/page/" ++ show n ++ "/index.html"

-- | Generate index pages for every tag. Tags with at most
--   'tagPaginationThreshold' items render a single page with the full
--   list and rely on the client-side count toggle; larger tags fall
--   back to server-side pagination at 'tagPageSize' per page.
--
--   Each tag's context is augmented with its sidecar, if present, so
--   the template can render a @$portal-intro$@ section and (later)
--   a See Also block keyed on @$portal-tooltip$@.
--
--   @baseCtx@ should be @siteCtx@ (passed in to avoid a circular import).
applyTagRules :: Tags -> [(String, String)] -> Context String -> Rules ()
applyTagRules tags portalPairs baseCtx = do
    -- Hakyll's @**/*@ glob needs a subdirectory level, so the flat and
    -- nested sidecar paths each need their own pattern. Keep this list
    -- in sync with the matching rule in Site.rules.
    sidecarIds <- getMatches ("content/tag-meta/*.md" .||. "content/tag-meta/**/*.md")
    let sidecarSet = Set.fromList sidecarIds
    tagsRules tags $ \tag pat -> do
        let itemCount = length (fromMaybe [] (lookup tag (tagsMap tags)))
            saCtx     = seeAlsoContext portalPairs tags tag
        if itemCount <= tagPaginationThreshold
            then clientPaginatedRule tag pat sidecarSet saCtx baseCtx
            else serverPaginatedRule tag pat sidecarSet saCtx baseCtx

-- | Single-page tag index: the count toggle runs client-side against
--   the full list. No server-side pagination, no @page/N@ URLs.
clientPaginatedRule :: String
                    -> Pattern
                    -> Set Identifier
                    -> Context String  -- ^ See Also contribution
                    -> Context String  -- ^ base (siteCtx)
                    -> Rules ()
clientPaginatedRule tag pat sidecarSet saCtx baseCtx = do
    route idRoute
    compile $ do
        scCtx <- sidecarContext sidecarSet tag
        items <- recentFirstByDisplay =<< loadAll (pat .&&. hasNoVersion)
        let ctx = listField "items" (tagItemCtx tag) (return items)
               <> constField "tag"       tag
               <> constField "title"     tag
               <> constField "list-page" "true"
               <> saCtx
               <> scCtx
               <> baseCtx
        makeItem ""
            >>= loadAndApplyTemplate "templates/tag-index.html"  ctx
            >>= loadAndApplyTemplate "templates/default.html"    ctx
            >>= relativizeUrls

-- | Display date of an identifier: the most-recent @revised:@ entry's
--   date when present and parseable, else the creation date. Mirrors
--   the (unexported) @itemDisplayUTC@ behind 'Contexts.recentFirstByDisplay',
--   but needs only 'MonadMetadata' — the paginate grouper runs in
--   'Rules' over bare 'Identifier's, where no 'Item's exist yet.
identifierDisplayUTC :: (MonadMetadata m, MonadFail m)
                     => Identifier -> m UTCTime
identifierDisplayUTC ident = do
    meta <- getMetadata ident
    case getRevisions meta of
        (r:_) | Just utc <- (parseTimeM True defaultTimeLocale "%Y-%m-%d"
                                 (revisionDateISO r) :: Maybe UTCTime)
              -> return utc
        _ -> getItemUTC defaultTimeLocale ident

-- | Partition identifiers into pages of @n@, most recent first by
--   /display/ date — the same revision-aware key
--   'recentFirstByDisplay' sorts by within each rendered page — so
--   cross-page ordering is monotone. With creation-date partitioning
--   (plain @sortRecentFirst@), a recently revised old item stayed on a
--   late page but jumped to its top; now it migrates to the early page
--   where its displayed date says it belongs.
sortAndGroupByDisplayAt :: (MonadMetadata m, MonadFail m)
                        => Int -> [Identifier] -> m [[Identifier]]
sortAndGroupByDisplayAt n ids = do
    keyed <- mapM (\i -> (,) <$> identifierDisplayUTC i <*> pure i) ids
    return $ paginateEvery n $ map snd $ sortBy (flip (comparing fst)) keyed

-- | Server-side pagination at 'tagPageSize' per page. Previous/next
--   navigation renders via @templates/partials/paginate-nav.html@;
--   the count toggle operates within the current page only. Pages are
--   partitioned and sorted by the same display-date key (see
--   'sortAndGroupByDisplayAt').
serverPaginatedRule :: String
                    -> Pattern
                    -> Set Identifier
                    -> Context String  -- ^ See Also contribution
                    -> Context String  -- ^ base (siteCtx)
                    -> Rules ()
serverPaginatedRule tag pat sidecarSet saCtx baseCtx = do
    paginate <- buildPaginateWith (sortAndGroupByDisplayAt tagPageSize) pat (tagPageId tag)
    paginateRules paginate $ \pageNum pat' -> do
        route idRoute
        compile $ do
            scCtx <- sidecarContext sidecarSet tag
            items <- recentFirstByDisplay =<< loadAll (pat' .&&. hasNoVersion)
            let ctx = listField "items" (tagItemCtx tag) (return items)
                   <> paginateContext paginate pageNum
                   <> constField "tag"       tag
                   <> constField "title"     tag
                   <> constField "list-page" "true"
                   <> saCtx
                   <> scCtx
                   <> baseCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/tag-index.html"  ctx
                >>= loadAndApplyTemplate "templates/default.html"    ctx
                >>= relativizeUrls

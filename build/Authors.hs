{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Author system — treats authors like tags.
--
--   Author pages live at /authors/{slug}/index.html.
--   Items with no "authors" frontmatter key default to Levi Neuwirth.
--
--   Frontmatter format (name-only or name|url — url part is ignored now):
--     authors:
--       - "Levi Neuwirth"
--       - "Alice Smith | https://alice.example"   -- url ignored; link goes to /authors/alice-smith/
module Authors
    ( buildAllAuthors
    , applyAuthorRules
    ) where

import Hakyll
import Pagination           (sortAndGroup)
import Patterns             (authorIndexable)
import Contexts             (abstractField, tagLinksField, canonicalUrlField)
import Utils                (authorSlugify, itemAuthors)
import Tags                 (anchoredTagsRules)


-- ---------------------------------------------------------------------------
-- Constants
-- ---------------------------------------------------------------------------

-- | Content patterns indexed by author. Sourced from 'Patterns.authorIndexable'
-- so this stays in lockstep with Tags.hs and Backlinks.hs.
allContent :: Pattern
allContent = authorIndexable


-- ---------------------------------------------------------------------------
-- Tag-like helpers (mirror of Tags.hs)
-- ---------------------------------------------------------------------------

-- | The authors an identifier credits ('Utils.itemAuthors'), the same
--   list its byline shows.
getAuthors :: MonadMetadata m => Identifier -> m [String]
getAuthors ident = itemAuthors <$> getMetadata ident

-- | Canonical identifier for an author's index page (page 1).
authorIdentifier :: String -> Identifier
authorIdentifier name = fromFilePath $ "authors/" ++ authorSlugify name ++ "/index.html"

-- | Paginated identifier: page 1 → authors/{slug}/index.html
--                         page N → authors/{slug}/page/N/index.html
authorPageId :: String -> PageNumber -> Identifier
authorPageId slug 1 = fromFilePath $ "authors/" ++ slug ++ "/index.html"
authorPageId slug n = fromFilePath $ "authors/" ++ slug ++ "/page/" ++ show n ++ "/index.html"


-- ---------------------------------------------------------------------------
-- Build + rules
-- ---------------------------------------------------------------------------

buildAllAuthors :: Rules Tags
buildAllAuthors = buildTagsWith getAuthors allContent authorIdentifier

applyAuthorRules :: Tags -> Context String -> Rules ()
applyAuthorRules authors baseCtx = anchoredTagsRules "_dependencies/authors" authors $ \name pat -> do
    let slug = authorSlugify name
    paginate <- buildPaginateWith sortAndGroup pat (authorPageId slug)
    paginateRules paginate $ \pageNum pat' -> do
        route idRoute
        compile $ do
            items <- recentFirst =<< loadAll (pat' .&&. hasNoVersion)
            let ctx = listField "items" itemCtx (return items)
                   <> paginateContext paginate pageNum
                   <> constField "author" name
                   <> constField "title"  name
                   <> constField "portal" "true"
                   -- C01: ahead of baseCtx's descriptionField, whose
                   -- body-excerpt fallback would describe the first
                   -- listed piece rather than this index.
                   <> constField "description"
                        ("Writing on this site by " ++ name ++ ".")
                   <> baseCtx
            makeItem ""
                >>= loadAndApplyTemplate "templates/author-index.html" ctx
                >>= loadAndApplyTemplate "templates/default.html"      ctx
                >>= relativizeUrls
  where
    -- 'canonicalUrlField' rather than defaultContext's @$url$@: a
    -- directory-routed essay's route is @essays/x/index.html@, and the
    -- author index is the reader's way in to a page whose canonical
    -- link, sitemap entry and feed id all say @/essays/x/@ (audit C03).
    itemCtx = dateField "date" "%-d %B %Y"
           <> tagLinksField "item-tags"
           <> abstractField
           <> canonicalUrlField
           <> defaultContext



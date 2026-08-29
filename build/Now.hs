{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Now page: loads data/now.yaml and renders the active-projects view
-- and the recently-shipped archive for /current.html. Page-level
-- "Last updated" stamp is exposed as a context field; relative time
-- ("4 days ago") is computed at build time from getCurrentTime.
module Now
    ( nowCtx
    ) where

import Data.Aeson         (FromJSON (..), withObject, (.:), (.:?), (.!=))
import Data.Char          (toUpper)
import Data.List          (nub, sortBy)
import Data.Maybe         (fromMaybe)
import Data.Ord           (Down (..), comparing)
import Data.Time.Calendar (Day, diffDays)
import Data.Time.Clock    (UTCTime (..), getCurrentTime)
import Data.Time.Format   (defaultTimeLocale, formatTime, parseTimeM)
import qualified Data.Text             as T
import qualified Data.Text.Encoding    as TE
import qualified Data.Yaml             as Y
import Hakyll hiding (escapeHtml)
import Contexts (siteCtx)
import Utils    (escapeHtml)

-- ---------------------------------------------------------------------------
-- Entry types
-- ---------------------------------------------------------------------------

data NowEntry = NowEntry
    { neTitle    :: String
    , neSection  :: String
    , neStatus   :: String
    , neUpdated  :: String
    , neLink     :: Maybe String
    , neNote     :: Maybe String
    , nePriority :: Int
    }

instance FromJSON NowEntry where
    parseJSON = withObject "NowEntry" $ \o -> NowEntry
        <$> o .:  "title"
        <*> o .:  "section"
        <*> o .:  "status"
        <*> o .:  "updated"
        <*> o .:? "link"
        <*> o .:? "note"
        <*> o .:? "priority" .!= 0

data NowShipped = NowShipped
    { nsTitle     :: String
    , nsCompleted :: String
    , nsLink      :: Maybe String
    , nsNote      :: Maybe String
    }

instance FromJSON NowShipped where
    parseJSON = withObject "NowShipped" $ \o -> NowShipped
        <$> o .:  "title"
        <*> o .:  "completed"
        <*> o .:? "link"
        <*> o .:? "note"

data NowDoc = NowDoc
    { nLastUpdated :: String
    , nEntries     :: [NowEntry]
    , nShipped     :: [NowShipped]
    }

instance FromJSON NowDoc where
    parseJSON = withObject "NowDoc" $ \o -> NowDoc
        <$> o .:  "last-updated"
        <*> o .:? "entries" .!= []
        <*> o .:? "shipped" .!= []

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

-- | Section ordering follows first-appearance in entries. Reorder the
--   YAML to reorder the page; no separate ordering key required.
sectionOrder :: [NowEntry] -> [String]
sectionOrder = nub . map neSection

-- | Status ordering — "how close to shipping." Lower rank sorts first.
--   Statuses not listed sort below all known ones (rank 99) so a typo
--   surfaces visibly at the bottom of its section instead of silently
--   ranking next-to-the-top.
statusRanks :: [(String, Int)]
statusRanks =
    [ ("accepted",    0)
    , ("in-review",   1)
    , ("revising",    2)
    , ("drafting",    3)
    , ("building",    4)
    , ("early-stage", 5)
    , ("paused",      6)
    ]

statusRank :: String -> Int
statusRank s = fromMaybe 99 (lookup s statusRanks)

-- | Three-tier sort key for active entries:
--     1. priority   — manual override; higher floats up (default 0)
--     2. statusRank — how close to shipping (lower is closer)
--     3. updated    — recency tiebreaker within the same rank
--   Sectioning is applied to the *unsorted* list so section ordering
--   continues to follow YAML source order; sorting happens within each
--   section's filtered slice.
entrySortKey :: NowEntry -> (Down Int, Int, Down String)
entrySortKey e =
    ( Down (nePriority e)
    , statusRank (neStatus e)
    , Down (neUpdated e)
    )

-- | "early-stage" → "Early Stage", "research" → "Research".
titleCaseWords :: String -> String
titleCaseWords = unwords . map cap . wordsOnDash
  where
    cap []     = []
    cap (x:xs) = toUpper x : xs
    wordsOnDash s = case break (== '-') s of
        (a, [])     -> [a]
        (a, _:rest) -> a : wordsOnDash rest

-- ---------------------------------------------------------------------------
-- HTML rendering
-- ---------------------------------------------------------------------------

renderStatusChip :: String -> String
renderStatusChip s = concat
    [ "<span class=\"now-status now-status--", escapeHtml s, "\">"
    , escapeHtml (titleCaseWords s)
    , "</span>"
    ]

-- | Active-entry card. Reuses the .item-card / .item-card-* classes from
--   item-card.css so the Now page picks up the existing typographic
--   register; the .now-* classes layer status-chip + spacing on top.
renderEntry :: NowEntry -> String
renderEntry e = concat
    [ "<li class=\"item-card now-card\">"
    , "<span class=\"item-card-kind now-kind\">"
    , renderStatusChip (neStatus e)
    , "</span>"
    , "<div class=\"item-card-main\">"
    , "<div class=\"item-card-header\">"
    , renderTitle (neLink e) (neTitle e)
    , "<time class=\"item-card-date\" datetime=\"", escapeHtml (neUpdated e), "\">"
    , escapeHtml (neUpdated e)
    , "</time>"
    , "</div>"
    , maybe "" (\n -> "<p class=\"item-card-abstract is-full\">" ++ escapeHtml n ++ "</p>") (neNote e)
    , "</div>"
    , "</li>"
    ]

renderShippedEntry :: NowShipped -> String
renderShippedEntry s = concat
    [ "<li class=\"item-card now-card now-card--shipped\">"
    , "<span class=\"item-card-kind now-kind\">"
    , renderStatusChip "shipped"
    , "</span>"
    , "<div class=\"item-card-main\">"
    , "<div class=\"item-card-header\">"
    , renderTitle (nsLink s) (nsTitle s)
    , "<time class=\"item-card-date\" datetime=\"", escapeHtml (nsCompleted s), "\">"
    , escapeHtml (nsCompleted s)
    , "</time>"
    , "</div>"
    , maybe "" (\n -> "<p class=\"item-card-abstract is-full\">" ++ escapeHtml n ++ "</p>") (nsNote s)
    , "</div>"
    , "</li>"
    ]

renderTitle :: Maybe String -> String -> String
renderTitle mu title = case mu of
    Just url -> "<a class=\"item-card-title\" href=\"" ++ escapeHtml url ++ "\">" ++ escapeHtml title ++ "</a>"
    Nothing  -> "<span class=\"item-card-title\">" ++ escapeHtml title ++ "</span>"

renderSection :: String -> [NowEntry] -> String
renderSection sec es = concat
    [ "<section class=\"now-section library-section\">"
    , "<h2 class=\"now-section-heading\">"
    , escapeHtml (titleCaseWords sec)
    , "</h2>"
    , "<ul class=\"item-card-list\">"
    , concatMap renderEntry es
    , "</ul>"
    , "</section>"
    ]

renderEntries :: [NowEntry] -> String
renderEntries [] = ""
renderEntries entries = concatMap renderOne (sectionOrder entries)
  where
    renderOne sec =
        let inSec = filter ((== sec) . neSection) entries
            sorted = sortBy (comparing entrySortKey) inSec
        in renderSection sec sorted

renderShippedAll :: [NowShipped] -> String
renderShippedAll [] = ""
renderShippedAll items = concat
    [ "<section class=\"now-section now-section--shipped library-section\">"
    , "<h2 class=\"now-section-heading\">Recently Shipped</h2>"
    , "<ul class=\"item-card-list\">"
    , concatMap renderShippedEntry sorted
    , "</ul>"
    , "</section>"
    ]
  where
    sorted = sortBy (comparing (Down . nsCompleted)) items

-- ---------------------------------------------------------------------------
-- Date formatters — runs at build time
-- ---------------------------------------------------------------------------

-- | "2026-04-26" → "26 April 2026". Falls back to the raw ISO string
--   if the date is unparseable, so a typo in @last-updated@ surfaces
--   in the rendered page rather than blowing up the build.
formatWriterly :: String -> String
formatWriterly iso =
    case parseTimeM True defaultTimeLocale "%Y-%m-%d" iso :: Maybe Day of
        Nothing -> iso
        Just d  -> formatTime defaultTimeLocale "%-d %B %Y" d

relativeTime :: Day -> String -> String
relativeTime today iso =
    case parseTimeM True defaultTimeLocale "%Y-%m-%d" iso :: Maybe Day of
        Nothing -> ""
        Just d  -> bucket (diffDays today d)
  where
    bucket n
        | n <  0    = ""
        | n == 0    = "today"
        | n == 1    = "yesterday"
        | n <  7    = show n ++ " days ago"
        | n < 28    = pluralize (n `div` 7)  "week"
        | n < 365   = pluralize (n `div` 30) "month"
        | otherwise = pluralize (n `div` 365) "year"
    pluralize 1 unit = "1 " ++ unit ++ " ago"
    pluralize k unit = show k ++ " " ++ unit ++ "s ago"

-- ---------------------------------------------------------------------------
-- Load
-- ---------------------------------------------------------------------------

-- | UTF-8 round-trip String → ByteString. Hakyll's @getResourceBody@
--   hands us a 'String' (Unicode codepoints); the yaml library wants
--   a UTF-8 'ByteString'. 'Data.ByteString.Char8.pack' would truncate
--   each 'Char' to 8 bits — fine for ASCII, silent corruption for any
--   codepoint above 0x7F (e.g. em-dash 0x2014 → control char 0x14).
loadNow :: Compiler NowDoc
loadNow = do
    rawItem <- load (fromFilePath "data/now.yaml") :: Compiler (Item String)
    case Y.decodeEither' (TE.encodeUtf8 (T.pack (itemBody rawItem))) of
        Left  err -> fail ("now.yaml: " ++ show err)
        Right doc -> return doc

-- ---------------------------------------------------------------------------
-- Context
-- ---------------------------------------------------------------------------

nowCtx :: Context String
nowCtx =
    constField "now" "true"
    <> field "now-last-updated" (\_ -> nLastUpdated <$> loadNow)
    <> field "now-last-updated-display" (\_ -> formatWriterly . nLastUpdated <$> loadNow)
    <> field "now-last-updated-relative" (\_ -> do
        doc  <- loadNow
        nowT <- unsafeCompiler getCurrentTime
        let today = utctDay nowT
            rel   = relativeTime today (nLastUpdated doc)
        if null rel
            then noResult "no relative time"
            else return rel
      )
    <> field "now-entries-html" (\_ -> renderEntries . nEntries <$> loadNow)
    <> field "now-shipped-html" (\_ -> renderShippedAll . nShipped <$> loadNow)
    <> siteCtx

{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Shared utilities used across the build system.
--
-- The HTML escapers (one for 'String', one for 'Text') live here so that
-- every filter, context, and renderer goes through the same definition.
-- The expansion order matters: @&@ MUST be replaced first, otherwise the
-- @&amp;@ injected by other rules gets re-escaped to @&amp;amp;@. The
-- pure-character-by-character implementation used here avoids that hazard
-- entirely (each character is mapped exactly once).
module Utils
    ( wordCount
    , readingTime
    , escapeHtml
    , escapeHtmlText
    , trim
    , authorSlugify
    , authorNameOf
    ) where

import           Data.Char (isAlphaNum, isSpace, toLower)
import           Data.List (dropWhileEnd)
import qualified Data.Text as T

-- | Count the number of words in a string (split on whitespace).
wordCount :: String -> Int
wordCount = length . words

-- | Estimate reading time in minutes (assumes 200 words per minute).
-- Rounds up — 399 words is 2 minutes, not 1. Minimum is 1 minute.
readingTime :: String -> Int
readingTime s = max 1 ((wordCount s + 199) `div` 200)

-- | Escape HTML special characters: @&@, @<@, @>@, @\"@, @\'@.
--
-- Safe for use in attribute values and text content. The order of the
-- @case@ branches is irrelevant — each input character maps to exactly
-- one output sequence.
escapeHtml :: String -> String
escapeHtml = concatMap escChar
  where
    escChar '&'  = "&amp;"
    escChar '<'  = "&lt;"
    escChar '>'  = "&gt;"
    escChar '"'  = "&quot;"
    escChar '\'' = "&#39;"
    escChar c    = [c]

-- | 'Text' counterpart of 'escapeHtml'.
escapeHtmlText :: T.Text -> T.Text
escapeHtmlText = T.concatMap escChar
  where
    escChar '&'  = "&amp;"
    escChar '<'  = "&lt;"
    escChar '>'  = "&gt;"
    escChar '"'  = "&quot;"
    escChar '\'' = "&#39;"
    escChar c    = T.singleton c

-- | Strip leading and trailing whitespace.
trim :: String -> String
trim = dropWhileEnd isSpace . dropWhile isSpace

-- | Lowercase a string, drop everything that isn't alphanumeric or
-- space, then replace each space with a hyphen. Note that a run of
-- spaces therefore becomes a run of hyphens (@"A  B" → "a--b"@) —
-- deliberately left as-is, since every slug on the site is generated
-- by this one function and collapsing runs now would move existing
-- author URLs.
--
-- Used for author URL slugs (e.g. @"Levi Neuwirth" → "levi-neuwirth"@).
-- Centralised here so 'Authors' and 'Contexts' cannot drift on Unicode
-- edge cases.
authorSlugify :: String -> String
authorSlugify = map (\c -> if c == ' ' then '-' else c)
              . filter (\c -> isAlphaNum c || c == ' ')
              . map toLower

-- | Extract the author name from a "Name | url" frontmatter entry.
-- The URL portion is dropped (it's no longer used by the author system,
-- which routes everything through @/authors/{slug}/@).
authorNameOf :: String -> String
authorNameOf s = trim (takeWhile (/= '|') s)

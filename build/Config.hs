{-# LANGUAGE OverloadedStrings #-}
-- | Site-owned identity and feeds. Rule construction reads this explicitly
-- in 'preprocess'; compilers use 'loadConfig', so site.yaml is a real Hakyll
-- dependency. There is deliberately no process-global configuration.
module Config
    ( SiteConfig (..), FeedSpec (..), FeedSection (..)
    , configRules, readSiteConfig, loadConfig, configField
    , renderSiteFeed, configMake, photoFeed, sectionName, loadFeed
    , siteOwnHosts
    ) where

import Control.Monad (unless, when)
import Data.Aeson (FromJSON (..), ToJSON (..), Object,
                   withObject, withText, object, (.:), (.:?), (.!=), (.=), encode)
import Data.Aeson.Types (Parser)
import qualified Data.Aeson.Key as Key
import qualified Data.Aeson.KeyMap as KM
import qualified Data.ByteString as BS
import qualified Data.ByteString.Lazy as LBS
import Data.Char (isControl, toLower, toUpper)
import Data.List (find, intercalate, isPrefixOf, isSuffixOf, nub, stripPrefix)
import Data.Maybe (fromMaybe)
import qualified Data.Text as T
import qualified Data.Text.Encoding as TE
import Data.Time.Clock (getCurrentTime)
import Data.Time.Format (defaultTimeLocale, formatTime)
import qualified Data.Yaml as Yaml
import Hakyll hiding (escapeHtml)
import System.FilePath (splitDirectories)
import Utils (escapeHtml)

data SiteConfig = SiteConfig
    { siteTitle :: String
    , siteAuthor :: String
    , siteAuthorSort :: String
    , siteEmail :: String
    , siteContactEmail :: String
    , siteUrl :: String
    , siteHost :: String
    , siteSourceRepo :: String
    , siteSourceBranch :: String
    , siteForgeHost :: String
    , siteContentLicense :: String
    , siteCodeLicense :: String
    , siteFeeds :: [FeedSpec]
    } deriving (Eq, Show)

data FeedSection = Essays | Blog | Fiction | Poetry | Music | Photos
    deriving (Eq, Show)

sectionName :: FeedSection -> String
sectionName s = case s of
    Essays -> "essays"
    Blog -> "blog"
    Fiction -> "fiction"
    Poetry -> "poetry"
    Music -> "music"
    Photos -> "photography"

instance FromJSON FeedSection where
    parseJSON = withText "feed section" $ \s -> case s of
        "essays" -> pure Essays
        "blog" -> pure Blog
        "fiction" -> pure Fiction
        "poetry" -> pure Poetry
        "music" -> pure Music
        "photography" -> pure Photos
        _ -> fail ("unknown feed section: " ++ T.unpack s)

instance ToJSON FeedSection where
    toJSON = toJSON . sectionName

data FeedSpec = FeedSpec
    { feedPath :: FilePath
    , feedName :: String
    , feedSummary :: String
    , feedSections :: [FeedSection]
    , feedAdvertise :: Bool
    , feedLimit :: Maybe Int
    } deriving (Eq, Show)

instance FromJSON FeedSpec where
    parseJSON = withObject "feed" $ \o -> do
        onlyKeys ["path", "title", "description", "sections", "advertise", "limit"] o
        f <- FeedSpec <$> o .: "path" <*> o .: "title" <*> o .: "description"
                      <*> o .: "sections" <*> o .:? "advertise" .!= True
                      <*> o .:? "limit"
        mapM_ (uncurry singleLine)
            [("feed path", feedPath f), ("feed title", feedName f),
             ("feed description", feedSummary f)]
        unless (safePath (feedPath f) && ".xml" `isSuffixOf` feedPath f) $
            fail "feed path must be a relative .xml path without traversal"
        when (null (feedSections f) || nub (feedSections f) /= feedSections f) $
            fail "feed sections must be nonempty and unique"
        when (Photos `elem` feedSections f && not (photoFeed f)) $
            fail "photography feeds must contain only the photography section"
        when (maybe False (<= 0) (feedLimit f)) $
            fail "feed limit must be positive, or null for all entries"
        pure f

instance ToJSON FeedSpec where
    toJSON f = object
        [ "path" .= feedPath f, "title" .= feedName f
        , "description" .= feedSummary f, "sections" .= feedSections f
        , "advertise" .= feedAdvertise f, "limit" .= feedLimit f ]

instance FromJSON SiteConfig where
    parseJSON = withObject "site config" $ \o -> do
        onlyKeys (map Key.fromString identityKeys ++ ["feeds"]) o
        c <- SiteConfig <$> o .: "title" <*> o .: "author" <*> o .: "author-sort"
                        <*> o .: "email" <*> o .: "contact-email"
                        <*> o .: "url" <*> o .: "host"
                        <*> o .: "source-repo" <*> o .:? "source-branch" .!= "main"
                        <*> o .: "forge-host" <*> o .: "content-license"
                        <*> o .: "code-license" <*> o .: "feeds"
        mapM_ (uncurry singleLine) (identityValues c)
        mapM_ (\(name, value) -> unless (absoluteUrl value && not ("/" `isSuffixOf` value)) $
            fail (name ++ " must be an absolute HTTP(S) URL without a trailing slash"))
            [("url", siteUrl c), ("source-repo", siteSourceRepo c)]
        mapM_ (\value -> unless (all (`elem` (['a'..'z'] ++ ['0'..'9'] ++ ".-")) value) $
            fail "host and forge-host must be lowercase hostnames") [siteHost c, siteForgeHost c]
        -- Links to the host, with or without www., are this site's own; a
        -- host that disagrees with url would mark the site's links external.
        when (null (bareHost c)) $ fail "host must name a domain, not just www."
        unless (urlHost (siteUrl c) `elem` siteOwnHosts c) $
            fail "url's hostname must be host, with or without a leading www."
        mapM_ (\value -> unless (all (`elem` (['a'..'z'] ++ ['A'..'Z'] ++ ['0'..'9'] ++ "-._")) value) $
            fail "license identifiers must be safe file names") [siteContentLicense c, siteCodeLicense c]
        unless (safePath (siteSourceBranch c)) $ fail "source-branch must be a relative path without traversal"
        let paths = map feedPath (siteFeeds c)
        when (nub paths /= paths) $ fail "feed paths must be unique"
        pure c

instance ToJSON SiteConfig where
    toJSON c = object ([Key.fromString k .= v | (k, v) <- identityValues c]
                       ++ ["feeds" .= siteFeeds c])

identityKeys :: [String]
identityKeys = ["title", "author", "author-sort", "email", "contact-email", "url", "host",
                "source-repo", "source-branch", "forge-host", "content-license", "code-license"]

identityValues :: SiteConfig -> [(String, String)]
identityValues c = zip identityKeys
    [siteTitle c, siteAuthor c, siteAuthorSort c, siteEmail c, siteContactEmail c,
     siteUrl c, siteHost c, siteSourceRepo c, siteSourceBranch c, siteForgeHost c,
     siteContentLicense c, siteCodeLicense c]

onlyKeys :: [Key.Key] -> Object -> Parser ()
onlyKeys allowed o = unless (null unknown) $
    fail ("unknown configuration keys: " ++ intercalate ", " (map Key.toString unknown))
  where unknown = filter (`notElem` allowed) (KM.keys o)

singleLine :: String -> String -> Parser ()
singleLine name value = when (null value || any isControl value) $
    fail (name ++ " must be a nonempty single-line string")

safePath :: FilePath -> Bool
safePath path = not (null path) && not ("/" `isPrefixOf` path)
    && all (`notElem` [".", "..", ""]) (splitDirectories path)
    && not (any (`elem` ("\\?#:" :: String)) path)

absoluteUrl :: String -> Bool
absoluteUrl value = any (`isPrefixOf` value) ["https://", "http://"]
    && not (any (`elem` (" \t\r\n" :: String)) value)

-- | The lowercased hostname of an absolute HTTP(S) URL, without its
--   scheme, userinfo, port and path.
urlHost :: String -> String
urlHost url = map toLower (takeWhile (/= ':') (afterUserinfo authority))
  where
    authority = takeWhile (/= '/') (drop 3 (dropWhile (/= ':') url))
    afterUserinfo a = case break (== '@') a of
        (_, '@' : rest) -> rest
        _ -> a

-- | The hostnames that are this site's own: the configured host with and
--   without a leading @www.@, whichever of the two site.yaml names. Link
--   classification and the url check share this one definition.
siteOwnHosts :: SiteConfig -> [String]
siteOwnHosts c = [bareHost c, "www." ++ bareHost c]

bareHost :: SiteConfig -> String
bareHost c = fromMaybe (siteHost c) (stripPrefix "www." (siteHost c))

photoFeed :: FeedSpec -> Bool
photoFeed f = feedSections f == [Photos]

decodeConfig :: BS.ByteString -> Either String SiteConfig
decodeConfig = either (Left . ("site.yaml: " ++) . Yaml.prettyPrintParseException) Right
             . Yaml.decodeEither'

readSiteConfig :: IO SiteConfig
readSiteConfig = BS.readFile "site.yaml" >>= either fail pure . decodeConfig

configRules :: Rules ()
configRules = match "site.yaml" $ compile getResourceBody

loadConfig :: Compiler SiteConfig
loadConfig = loadBody "site.yaml" >>= either fail pure . decodeConfig . TE.encodeUtf8 . T.pack

loadFeed :: FilePath -> Compiler (SiteConfig, FeedSpec)
loadFeed path = do
    cfg <- loadConfig
    case find ((== path) . feedPath) (siteFeeds cfg) of
        Just feed -> pure (cfg, feed)
        Nothing -> fail ("site.yaml: feed removed; rebuild rules: " ++ path)

configField :: String -> (SiteConfig -> String) -> Context a
configField name get = field name $ \_ -> get <$> loadConfig

-- | Hakyll interpolates these into its feed templates as they are ("field
--   values are not escaped", @Hakyll.Web.Feed@), so a title such as
--   @Art & photography@ would make the feed invalid XML. Each is escaped
--   here, at the one place configuration meets the feed.
atomConfig :: SiteConfig -> FeedSpec -> FeedConfiguration
atomConfig c f = FeedConfiguration
    { feedTitle = escapeHtml (feedName f), feedDescription = escapeHtml (feedSummary f)
    , feedAuthorName = escapeHtml (siteAuthor c), feedAuthorEmail = escapeHtml (siteEmail c)
    , feedRoot = escapeHtml (siteUrl c) }

-- | Render a configured Atom feed, giving an empty one a valid @\<updated\>@.
--
--   Hakyll's 'renderAtom' derives the feed-level @updated@ from the first
--   item and falls back to the literal string @Unknown@ when the item list
--   is empty (@Hakyll.Web.Feed.renderFeed@). @Unknown@ is not an RFC 3339
--   timestamp: the feed is invalid, and the artifact gate
--   (@tools\/check-site.py@) rejects the build. A feed with no entries yet
--   is a legitimate state for any section of any site, so every empty feed
--   is kept and given the build time: honest, well formed, and it stops
--   changing the moment the first entry lands and a real date takes over.
--   A populated feed is never restamped.
renderSiteFeed :: SiteConfig -> FeedSpec -> Context String -> [Item String]
               -> Compiler (Item String)
renderSiteFeed c f ctx items = do
    feed <- renderAtom (atomConfig c f) ctx items
    if not (null items) then pure feed else do
        stamp <- unsafeCompiler $
            formatTime defaultTimeLocale "%Y-%m-%dT%H:%M:%SZ" <$> getCurrentTime
        pure (fmap (replaceFirst "<updated>Unknown</updated>"
                                 ("<updated>" ++ stamp ++ "</updated>")) feed)

-- | Replace the first occurrence of a literal substring. Returns the
--   input unchanged when the needle is absent.
replaceFirst :: String -> String -> String -> String
replaceFirst needle replacement = go
  where
    go [] = []
    go s@(c:cs) = case stripPrefix needle s of
        Just rest -> replacement ++ rest
        Nothing   -> c : go cs

-- | An includable GNU make fragment. Immediate defines keep '#' literal;
-- doubling '$' prevents make expansion, and an empty expression protects a
-- trailing backslash from consuming the newline. These are make values,
-- not shell-quoted arguments. JSON carries the complete typed config.
configMake :: SiteConfig -> String
configMake c = concatMap define
    ([("SITE_" ++ map (\x -> if x == '-' then '_' else toUpper x) k, v)
      | (k, v) <- identityValues c]
     ++ [("SITE_FEEDS", unwords (map feedPath (siteFeeds c))),
         ("SITE_CONFIG_JSON", T.unpack (TE.decodeUtf8 (LBS.toStrict (encode c))))])
  where
    define (name, value) = "define " ++ name ++ " :=\n"
        ++ concatMap (\x -> if x == '$' then "$$" else [x]) value
        ++ "$(subst ,,)\nendef\n"

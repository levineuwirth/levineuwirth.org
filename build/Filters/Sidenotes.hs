{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
-- | Convert Pandoc @Note@ inlines to inline sidenote HTML.
--
--   Each footnote becomes:
--   * A @<sup class="sidenote-ref">@ anchor in the body text.
--   * A @<span class="sidenote">@ immediately following it, containing
--     the rendered note content.
--
--   Additionally, every consumed note is re-emitted in a
--   @<section class="footnotes">@ appended at the document end. The
--   filter swallows Pandoc's own @Note@ inlines, so Pandoc's writer
--   never produces that section itself — without this re-emission,
--   narrow viewports with JavaScript disabled (where sidenotes.css
--   hides @.sidenote@ and sidenotes.js's bottom sheet never runs)
--   would lose footnote content entirely.
--
--   On wide viewports, sidenotes.css floats the spans into the right
--   margin and hides @section.footnotes@; on narrow viewports the
--   spans are hidden and the section is shown. The in-text anchor
--   targets the footnotes item (the only target visible on narrow
--   no-JS viewports); sidenotes.js intercepts clicks and pairs
--   ref\/note by element id, so the href is purely the no-JS path.
module Filters.Sidenotes (apply) where

import           Control.Monad.State.Strict
import           Data.Text                  (Text)
import qualified Data.Text                  as T
import           Text.Pandoc.Class          (runPure)
import           Text.Pandoc.Definition
import           Text.Pandoc.Shared         (stringify)
import           Text.Pandoc.Walk           (walk, walkM)
import           Text.Pandoc.Writers.HTML   (writeHtml5String)
import           PandocOptions              (writerOpts)
import           Utils                      (escapeHtmlText)

-- | Accumulator: next label counter plus collected notes
--   (newest-first; reversed before rendering the fallback section).
type NoteState = (Int, [(Text, [Block])])

-- | Transform all @Note@ inlines in the document to inline sidenote
--   HTML, and append the collected notes as a @section.footnotes@
--   fallback block.
apply :: Pandoc -> Pandoc
apply doc =
    let (Pandoc m blocks, (_, collected)) =
            runState (walkM convertNote doc) (1, [])
        notes = reverse collected
    in  Pandoc m $
            if null notes
                then blocks
                else blocks ++ [footnotesSection notes]

convertNote :: Inline -> State NoteState Inline
convertNote (Note blocks) = do
    (n, acc) <- get
    put (n + 1, (toLabel n, blocks) : acc)
    return $ RawInline "html" (renderNote n blocks)
convertNote x = return x

-- | The end-of-document fallback list. Letter labels are rendered
--   explicitly (an @<ol>@'s automatic numbering would disagree with
--   the in-text letters), so the list itself is unstyled.
footnotesSection :: [(Text, [Block])] -> Block
footnotesSection notes = RawBlock "html" $ T.concat $
    [ "<section class=\"footnotes\" role=\"doc-endnotes\">"
    , "<ol class=\"footnotes-list\">"
    ]
    ++ map item notes ++
    [ "</ol>"
    , "</section>"
    ]
  where
    item (lbl, blocks) = T.concat
        [ "<li id=\"fn-", lbl, "\" class=\"footnote-item\">"
        , "<span class=\"footnote-label\" aria-hidden=\"true\">", lbl, "</span>"
        , blocksToHtml (withoutIds blocks)
        , "<a href=\"#snref-", lbl
        , "\" class=\"footnote-back\" role=\"doc-backlink\""
        , " aria-label=\"Back to reference ", lbl, "\">\x21a9\xfe0e</a>"
        , "</li>"
        ]

-- | A note's blocks for the fallback copy, with every id removed.
--
--   The sidenote span renders the same blocks first, so any id inside a
--   note — a citation marker's @cite-back-\<n\>-\<k\>@, an explicit
--   @[text]{#id}@ — would otherwise appear twice on the page, and a link
--   to it would land on whichever copy came first anyway. The sidenote
--   keeps the ids; this copy carries none. Citation markers arrive as raw
--   HTML from "Citations", so raw HTML loses its @id@ attributes too.
withoutIds :: [Block] -> [Block]
withoutIds = walk inline . walk block
  where
    inline (Span  (_, c, kv) xs)   = Span  ("", c, kv) xs
    inline (Link  (_, c, kv) xs t) = Link  ("", c, kv) xs t
    inline (Image (_, c, kv) xs t) = Image ("", c, kv) xs t
    inline (Code  (_, c, kv) t)    = Code  ("", c, kv) t
    inline (RawInline f t)         = RawInline f (dropIdAttrs t)
    inline x                       = x
    block (Div       (_, c, kv) bs) = Div ("", c, kv) bs
    block (Header n  (_, c, kv) xs) = Header n ("", c, kv) xs
    block (CodeBlock (_, c, kv) t)  = CodeBlock ("", c, kv) t
    block (RawBlock f t)            = RawBlock f (dropIdAttrs t)
    block x                         = x

-- | Remove every @ id="…"@ attribute from an HTML fragment.
dropIdAttrs :: Text -> Text
dropIdAttrs t = case T.breakOn " id=\"" t of
    (before, rest)
        | T.null rest -> before
        | otherwise   -> before <> dropIdAttrs (T.drop 1 (T.dropWhile (/= '"') (T.drop 5 rest)))

-- | Convert a 1-based counter to a letter label using base-26 expansion
--   (Excel-column style): 1→a, 2→b, … 26→z, 27→aa, 28→ab, … 52→az,
--   53→ba, … 702→zz, 703→aaa.  Guarantees a unique label per counter so
--   no two sidenotes in a single document collide on @id="sn-…"@.
toLabel :: Int -> Text
toLabel n
    | n <= 0    = "?"
    | otherwise = T.pack (go n)
  where
    go k
        | k <= 0    = ""
        | otherwise =
            let (q, r) = (k - 1) `divMod` 26
            in go q ++ [toEnum (fromEnum 'a' + r)]

renderNote :: Int -> [Block] -> Text
renderNote n blocks =
    let inner = blocksToInlineHtml blocks
        lbl   = toLabel n
    in T.concat
        -- href targets the footnotes-section item: on narrow no-JS
        -- viewports that is the only visible rendering of the note
        -- (the adjacent .sidenote span is display:none there, and on
        -- wide viewports the note is already visible in the margin).
        -- sidenotes.js pairs ref/note by id and preventDefaults the
        -- click, so the href only ever navigates without JS.
        [ "<sup class=\"sidenote-ref\" id=\"snref-", lbl, "\">"
        ,   "<a href=\"#fn-", lbl, "\">", lbl, "</a>"
        , "</sup>"
        , "<span class=\"sidenote\" id=\"sn-", lbl, "\">"
        ,   "<sup class=\"sidenote-num\">", lbl, "</sup>\x00a0"
        ,   inner
        , "</span>"
        ]

-- | Render a list of Pandoc blocks for inclusion inside an inline @<span
--   class="sidenote">@.  Each top-level @Para@ is wrapped in a
--   @<span class="sidenote-para">@ instead of a @<p>@ (which would be
--   invalid inside a @<span>@); other block types are rendered with the
--   regular Pandoc HTML writer.
--
--   Operating on the AST is preferred over post-rendered string
--   substitution because the latter mangles content that legitimately
--   contains the literal text @<p>@ (e.g. code samples discussing HTML).
blocksToInlineHtml :: [Block] -> Text
blocksToInlineHtml = T.concat . map renderOne
  where
    renderOne :: Block -> Text
    renderOne (Para inlines) =
        "<span class=\"sidenote-para\">"
        <> inlinesToHtml inlines
        <> "</span>"
    renderOne (Plain inlines) =
        inlinesToHtml inlines
    renderOne b =
        blocksToHtml [b]

-- | Render a list of inlines to HTML (no surrounding @<p>@). Should the
--   writer ever fail, the note keeps its text, escaped, instead of
--   rendering empty without a word.
inlinesToHtml :: [Inline] -> Text
inlinesToHtml inlines =
    either (const (escapeHtmlText (stringify inlines))) id
        (runPure (writeHtml5String writerOpts (Pandoc mempty [Plain inlines])))

-- | Render a list of Pandoc blocks to an HTML fragment via a pure writer
--   run, with the same fallback.
blocksToHtml :: [Block] -> Text
blocksToHtml blocks =
    either (const (escapeHtmlText (stringify blocks))) id
        (runPure (writeHtml5String writerOpts (Pandoc mempty blocks)))

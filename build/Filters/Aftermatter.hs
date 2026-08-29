{-# LANGUAGE GHC2021 #-}
{-# LANGUAGE OverloadedStrings #-}
module Filters.Aftermatter (apply) where

import Text.Pandoc.Definition (Pandoc (..), Block (..), Format (..))

apply :: Pandoc -> Pandoc
apply (Pandoc meta blocks) = Pandoc meta (concatMap go blocks)
  where
    go (Div attr@(_, classes, _) content)
        | "aftermatter" `elem` classes
        = [dividerBlock, Div attr content]
    go b = [b]

dividerBlock :: Block
dividerBlock = RawBlock (Format "html")
    "<div class=\"aftermatter-divider\" aria-hidden=\"true\">\
    \<a href=\"/new.html\" class=\"aftermatter-logo\" aria-label=\"New\"></a>\
    \</div>"

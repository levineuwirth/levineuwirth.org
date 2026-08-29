---
title: "Speculative Reluctance"
date: 2026-04-15
abstract: >
  AI labs are likely deliberately reluctant to scale because they are aware that any imminient shift to locally run models as the norm would render their compute redundant. We take Anthropic as a principal case study to validate this hypothesis. 
tags:
  - ai
  - tech
  - speculative
  - open
status: "Draft"
confidence: 55
importance: 3
evidence: 1
scope: broad
novelty: moderate
practicality: high
history:
  - date: "2026-06-10"
  - date: "2026-04-17"
  - date: "2026-04-15"

---

Running a lab that develops frontier LLMs is somewhat like playing a game that, by all measurable metrics external, you are bound to lose. The amount of compute required to train a frontier LLM is unbelievably expensive. The expense of inference is even more astronomical. OpenAI claims at the time of this writing to have somewhere between 900 Million and 1 Billion active users, all of whom require some amount of inference cost, and some small subset of whom consume an enormous amount of compute - to use their words, this is ["commercial scale."](https://openai.com/index/accelerating-the-next-phase-ai/). This isn't to mention the immense amount of competition - there are many major players in the United States alone contributing models that push the boundaries. OpenAI may have been the first, but Anthropic, Google, Meta, xAI, and, yes, even Amazon and Bytedance are following right along. 

Then there's the news that the stock market doesn't want to hear. Ask yourself: who is deliberately left off the above list? If you're thinking of models like GLM, Qwen, MiniMax, and the notorious Deepseek, then we're on the same page. These models are rapidly approaching the capabilities of the frontier models that remain behind intrusive "competitive moats"^[This phrasing is adopted from Jared James Grogan's 2026 paper ["The End of the Foundation Model Era](https://arxiv.org/abs/2604.06217)] that do little more than violate the rights of their users. The advantages that such models provide are immense, and labs of the first list cannot ignore the likelihood of their precedence increasing in the weeks and months to come. In fact, I hypothesize that we are already seeing the reaction of frontier labs to these increasing capabilities, through the lense of juxtaposition: the jargon has remained constant, as if to negate any possibility of an "AI Bubble" bursting, but the quiet actions of the companies that aren't notoriously announced and decreed have shifted.

## The Dilemma
### Inference is the Name of the Game
Very few users of an LLM have ever attempted to train an LLM. Even those users who are technical powerhouses - and there are many of these^[Per OpenAI's account, Codex [has reached](https://openai.com/index/accelerating-the-next-phase-ai/) 2,000,000 active weekly users, and while I could not find any specific numbers that Anthropic has released regarding Claude Code's weekly user count, I presume it is higher than that of Codex.] -
likely are not intricately familiar with the inner workings of transformers. Even those who, perhaps from coursework, perhaps from curiosity, perhaps from [a chat](https://claude.ai/share/5282e1b8-24ce-4cf8-983e-55df95f5fbdc) with an LLM of choice have enough technical prowess to in theory write code that could facilitate the training of a naive transformer are unlikely to be able to train any model of substance, due to computational constraints. Consider, for instance, that [over 200,000 GPUs](https://x.ai/news/grok-3) were used to train Grok 3, which is a model from early 2025; the [aspirations of xAI](https://www.spacex.com/updates#xai-joins-spacex) in particular with regards to expansion of compute (into outer space) have, more recently, been the source of much controversy. To be absolutely precise, the inherent computational cost of training a model does not provide companies that do train models any safeguards nor guarantees that users cannot find more open alternatives.

Inference is the primary concern for multiple reasons. Inference is what creates the opportunity for an AI lab to generate revenue. Training a model, in principle, enables the capability for inference to be provided as a service to paying users, but there is no inherent revenue that is generated as a direct consequence of the training pipeline. Inference is also the primary logistical and computational concern. We have neglected in our previous discussion of training that training clusters may be provisioned; powerful GPUs are available to rent by the hour, and though doing this at the scale of training a frontier LLM is economically out of reach for the general population, for venture-capital backed startups, cash is abundantly available as a resource to burn. Inference, on the other hand, is not provisional; to provide inference at a scale that enables revenue, GPUs must be available to serve the requests of paying customers at all times. This is often not the case, as we will soon explore^[A detailed analysis of how even minute per-request inference costs scale to unfathomable overall costs is provided in CMU's ["Agents of Change."](https://www.cmu.edu/cmist/tech-and-policy/agents-of-change/index.html)].

## A deficit of compute
We are already seeing the extensive effects of the fact that inference cannot truly be provisioned at scale. Inference can be provisioned at smaller scales - indeed, as a student at Brown University, I make extensive use of our own [self-hosted interface](https://docs.ccv.brown.edu/ai-tools/services/librechat), which provides access to various frontier LLMs.

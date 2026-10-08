# Nestlé assistant smoke eval

Target: `https://app-backend-u6t5hmjsg6see.azurewebsites.net` · 18 questions (14 in scope, 4 out of scope).
Regenerate with `python evals/nestle_smoke.py --url <app url>`.

| Metric | RAG | RAG + GraphRAG |
| --- | --- | --- |
| Answered in-scope question | 14/14 (100%) | 14/14 (100%) |
| Cited a page from the right brand/section | 14/14 (100%) | 14/14 (100%) |
| Answer has inline `[page.md]` citation | 14/14 (100%) | 14/14 (100%) |
| Expected keywords in answer | 13/14 (93%) | 13/14 (93%) |
| Declined out-of-scope question | 4/4 (100%) | 4/4 (100%) |

## Per question

| Question | RAG source / cite | GraphRAG source / cite |
| --- | --- | --- |
| What can I make with Carnation hot chocolate? | ✓ / ✓ | ✓ / ✓ |
| What flavours of AERO bars are there? | ✓ / ✓ | ✓ / ✓ |
| Does KIT KAT contain peanuts? | ✓ / ✓ | ✓ / ✓ |
| Which KIT KAT products may contain peanuts? | ✓ / ✓ | ✓ / ✓ |
| What are the ingredients in a SMARTIES box? | ✓ / ✓ | ✓ / ✓ |
| Give me a recipe that uses KIT KAT. | ✓ / ✓ | ✓ / ✓ |
| What Häagen-Dazs ice cream flavours are available? | ✓ / ✓ | ✓ / ✓ |
| What is BOOST and who is it for? | ✓ / ✓ | ✓ / ✓ |
| Which NESCAFÉ instant coffees are sold in Canada? | ✓ / ✓ | ✓ / ✓ |
| What flavours does COFFEE MATE creamer come in? | ✓ / ✓ | ✓ / ✓ |
| Do DRUMSTICK cones contain nuts? | ✓ / ✓ | ✓ / ✓ |
| What TURTLES products are there? | ✓ / ✓ | ✓ / ✓ |
| How do I contact Nestlé Canada consumer services? | ✓ / ✓ | ✓ / ✓ |
| What MAGGI products can I cook with? | ✓ / ✓ | ✓ / ✓ |
| What is the capital of France? | declined | declined |
| How do I fix a flat bicycle tire? | declined | declined |
| What is Nestlé's share price today? | declined | declined |
| Who won the 2022 FIFA World Cup? | declined | declined |

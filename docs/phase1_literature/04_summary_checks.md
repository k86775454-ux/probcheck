# Summary checks

Prompt:

> Here is the abstract of a paper I have verified.
>
> Summarise it in three sentences: what they did, what they found, what it means for my problem about students assessing AI study answers. Do not add anything that is not in the abstract.

Marks: SUPPORTED (write the abstract phrase beside it) · NOT IN ABSTRACT (strike it, or keep it marked as your own inference) · CONTRADICTED (the abstract says otherwise: strike it and log it).


## Paper 1 — P1: Li et al. (2026)

Supporting Learners' Use of Imperfect Generative Pedagogical Chatbots: The Role of Chatbot Response Uncertainty and Reduced Verbosity. DOI: 10.1145/3772318.3791940.

Verification check: Exact-title search completed on 2026-10-06. Verified in ACM Digital Library; DOI 10.1145/3772318.3791940 confirmed from the publication record, and the abstract was read by the student.

### Abstract

Generative chatbots promise to scale personalized learning. Most publicly available generative chatbots are designed to provide confident and eloquent responses by default, even when hallucinating. Prior work has observed that learners using such chatbots often engage shallowly and fail to detect chatbot errors due to overtrust, cognitive overload, and prioritization of short-term gains. To address these challenges, this work examines two chatbot design options in a STEM learning context: introducing verbal uncertainty and reducing response verbosity. Using Bayesian causal inference and thematic analysis in a quasi-experimental setting, we found that a less verbose chatbot improved detection of errors with logical fallacies, but did not increase the use of alternative resources. A chatbot that always expressed uncertainty reduced the adoption of incorrect chatbot responses, but had mixed effects on learning outcomes, suggesting the need to increase signal credibility and maintain learners' engagement in the learning process despite chatbot disuse.

### AI summary and checks

| Sentence | Mark | Abstract phrase, or note |
|---|---|---|
| 1. The authors examined verbal uncertainty and reduced verbosity in STEM chatbots using a quasi-experimental approach. | SUPPORTED | “introducing verbal uncertainty and reducing response verbosity”; “in a quasi-experimental setting” |
| 2. Shorter responses helped detect logical fallacies without increasing alternative-resource use; a chatbot that always expressed uncertainty reduced incorrect-answer adoption but had mixed learning effects. | SUPPORTED | “improved detection of errors with logical fallacies”; “did not increase the use of alternative resources”; “reduced the adoption of incorrect chatbot responses”; “mixed effects on learning outcomes” |
| 3. Project inference: uncertainty prompts should be evaluated alongside students' engagement and learning. | NOT IN ABSTRACT | Project inference motivated by the reported “mixed effects on learning outcomes” and the need to “maintain learners' engagement”; the abstract does not directly test this project recommendation. |


## Paper 2 — P4: Spatharioti et al. (2025)

Effects of LLM-based Search on Decision Making: Speed, Accuracy, and Overreliance. DOI: 10.1145/3706598.3714082.

Verification check: Exact-title search completed on 2026-10-06. Verified in the DBLP publication record; DOI 10.1145/3706598.3714082 confirmed from the record, and the abstract was read by the student.

### Abstract

Recent advances in large language models (LLMs) are transforming online applications, including search tools that accommodate complex natural language queries and provide direct responses. There are, however, concerns about the veracity of LLM-generated content due to potential for LLMs to "hallucinate". In two online experiments, we examined how LLM-based search affects behavior compared to traditional search and explored ways to reduce over-reliance on incorrect LLM-based output. Participants assigned to LLM-based search completed tasks more quickly, with fewer but more complex queries, and reported a more satisfying experience. While decision accuracy was comparable when the LLM was correct, users overrelied on incorrect information when the model erred. In a second experiment, a color-coded highlighting system helped users detect errors, improving decision accuracy without affecting other outcomes. These findings suggest that LLM-based search tools have promise as decision aids but also highlight the importance of effectively communicating uncertainty to mitigate overreliance.

### AI summary and checks

| Sentence | Mark | Abstract phrase, or note |
|---|---|---|
| 1. Two online experiments compared LLM-based search with traditional search and examined an intervention against overreliance. | SUPPORTED | “In two online experiments”; “compared to traditional search”; “explored ways to reduce over-reliance on incorrect LLM-based output” |
| 2. LLM-based search was faster, but users overrelied on incorrect information when the model erred; color-coded highlighting improved error detection and decision accuracy. | SUPPORTED | “completed tasks more quickly”; “users overrelied on incorrect information when the model erred”; “a color-coded highlighting system helped users detect errors, improving decision accuracy” |
| 3. Project inference: color-coded uncertainty cues are a candidate for testing in a student study assistant. | NOT IN ABSTRACT | The abstract reports benefits from a “color-coded highlighting system”, but it does not test this intervention in a student learning assistant. |
# Module 4 offline evaluation

Run from `module-04/`:

~~~bash
python -m pytest -q
~~~

On 2026-09-26, 42 tests passed. They include 25 fictional scenario fixtures and focused tests of correction, atomicity, session isolation, expiry, deletion, retention choice, and invalid model output. The scripted scenarios check Python behavior against prewritten model proposals. They do **not** measure the accuracy of a live model, clinical safety, legal compliance, or robustness against real prompt injection.

One known failure mode remains: a model can propose a schema-valid fact that the customer never supplied. The application labels it as reported and permits review/correction, but it cannot verify the extraction from JSON structure alone. Live evaluation, evidence checks, and human review are separate work.

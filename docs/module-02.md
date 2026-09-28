# Module 2 — Add Multi-Turn Healthcare Support to the Same Web App

> **Project:** Customer Support LLM
>
> **Build:** Web app v0.2 — bounded conversation context
>
> **Learning loop:** Build → Break → Measure → Improve
>
> **Code:** [The same Django app, Module 2 stage](https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/webapp)

## Module mission

Module 1 answered one message at a time. In Module 2, a follow-up can refer to something the customer said earlier. We add a short history to the same web app and retain it in a Django server-side session. We do not build a separate chatbot package for this stage.

Healthcare support is our teaching context, but the app has no medical database or clinical validation. Use fictional messages. Personal diagnosis, prescribing, treatment, and emergency decisions are outside the app's authority.

## Learning outcomes

You will be able to explain how messages become model context, bound the amount of context sent, keep different browser sessions separate, commit a turn only after success, and test a provider failure without spending API credits.

## 1. Continue the running app

Follow the setup in [Module 1](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/docs/module-01.md) and open `http://127.0.0.1:8000/?stage=2`. The same [home template](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/templates/support/home.html) now displays recent conversation bubbles. The same `/chat/<stage>/` view sends the form to the shared service.

Try two messages in order:

1. “My order is A123.”
2. “What is my order number?”

The offline teaching backend can refer to A123 in the second response and say that it cannot verify the order's status. Switch to Stage 1 and ask the second message alone. That version has no earlier turn to use.

## 2. Represent a conversation explicitly

The service stores short role-labeled messages in `m2_history` within Django's server-side session:

~~~python
{"role": "user", "content": "My order is A123"}
{"role": "assistant", "content": "..."}
~~~

Roles and ordering matter. Sending only the latest text loses reference to A123. Sending every past message forever increases cost, can preserve outdated statements, and exposes unnecessary data to a provider. The [service](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/service.py) limits stored context to the latest eight messages, or roughly four exchanges. That fixed bound is a learning-stage choice, not an optimal universal limit.

The browser receives a session cookie; the messages live on the server, not inside that cookie. A different browser session gets a different history. There is no account authentication yet, so this does not prove the identity of a real customer.

## 3. Treat a turn as a transaction

The service builds the model request from the existing history plus the new user message. It calls the shared [gateway](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/gateway.py). Only if a nonempty response arrives does it save the new user and assistant messages together.

Why commit after success? Suppose the provider fails after receiving the user's text. If we saved the user message first, a retry could leave a half-finished turn in history. The next response might treat that failed attempt as an earlier completed conversation. The test suite injects a failing generator and confirms that history remains unchanged.

The app displays a controlled error when generation fails. It does not show provider stack traces or credentials in the customer interface. This is still a prototype: production systems need bounded retry rules, observability, rate limits, and a clear policy for data retention.

## 4. Add healthcare support boundaries

Stage 2 instructions ask for concise support, no invented clinic facts, and qualified human review for clinical decisions. Try fictional requests such as “I have a headache; what dose should I take?” The offline response routes the person to a support professional and does not prescribe. It has no triage engine or emergency classification.

A successful demo is not clinical evidence. Even a model that refuses several unsafe examples can fail on new wording or a long conversation. Do not enter real patient details in this course app. Module 4 will add explicit reported-fact state, corrections, deletion, and expiry; none of those makes the system a medical device.

## 5. Break and measure the flow

Run `python manage.py test support` from `webapp/`. The Module 2 integration test checks the follow-up, the eight-message limit, and the atomic failure behavior. In a second browser session, verify that the earlier order reference is absent. Use the **Reset module** button to clear the current short history.

Record for each fictional scenario: the first message, follow-up, whether context was used correctly, whether a claim remained unverified, how many messages were sent, latency, and any failure. Compare Stage 1 and Stage 2 on the same follow-up. Additional context can help with pronouns, but it can also carry stale or adversarial text.

## Module project

Show a two-turn support request in the browser, a reset that clears its history, and one controlled model failure that does not leave a partial turn. Explain why the app keeps a bounded recent history and why a customer-reported order number is not a verified backend result.

## What comes next

Module 3 adds versioned routing instructions and a validated JSON result to this same app. Conversation text alone is insufficient when Python must make an explicit routing decision.

[Continue to Module 3](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/knowledge-base/modules/module-03.md)

# AI Workflow Decision Navigator

[Open the interactive tool](https://www.lauraelizabethhand.com/resources/project-operations-tools/ai-workflow-decision-navigator/)

**What is the simplest reliable way to complete a task?** Answer six plain-language questions about the work, tools available, frequency, predictability, output, and sensitivity. The navigator recommends a starting point and identifies relevant software features to try.

It compares six approaches: existing software, a one-time prompt, a reusable prompt workflow, rule-based automation, a supervised AI agent, and a focused custom application. Each decision includes a rationale, implementation checklist, named platform capabilities, licensing cautions, a sample prompt, and a downloadable decision brief.

## How it works

The recommendations use transparent client-side decision rules rather than a remote language-model call. Examples include:

- Repeatable spreadsheet cleanup in Excel → try Power Query and other native features before adding AI.
- Repeated content drafting that requires review → test and standardize a prompt workflow.
- Clear event-driven requests across applications → assess a trigger/condition/action automation.
- Variable, multistep requests that require context-sensitive judgment → prototype a **supervised** agent only after testing less complex alternatives.
- A genuinely new public interface → validate the requirement and prototype a small custom tool.

"Configure an agent" means instructions, tool access, evaluation, escalation, and appropriate approvals. It does not necessarily mean fine-tuning or training a new AI model.

## Software capability guide — 29 programs

The navigator covers Excel, Word, PowerPoint, Outlook, Google Sheets, Google Docs, Gmail, Google Drive, Asana, Trello, ChatGPT, Gemini, Microsoft Copilot, Power Automate, Zapier, Google Forms, Microsoft Forms, Airtable, Notion, monday.com, Slack, HubSpot, Make, Power BI, Looker Studio, Canva, SharePoint, Microsoft Teams, and WordPress.

It connects task categories and plain-language clues (such as *spreadsheet*, *survey*, *CRM*, *dashboard*, and *form*) to possible features, prioritizing software the visitor has selected. Each recommendation explains a first step, a plan-specific limitation, a cost-access category, and a link to vendor guidance.

### Cost and licensing distinctions

- **Built-in / check your current software:** e.g. Excel Power Query, Word templates, Gmail filters, or Google Forms linking to Sheets. This means no additional tool is necessarily needed, not that every version is free.
- **Free but usage-limited:** e.g. Airtable automations, Trello automation runs, Make credits, or Zapier tasks.
- **Requires a qualifying paid plan:** e.g. Asana automation rules, monday.com automations, or Slack Workflow Builder. These products may still have usable free core functions.
- **Plan or tenant dependent:** e.g. Microsoft Copilot, Power Automate premium actions, Microsoft 365 administration, and certain AI features.

Checked against vendor documentation on October 21, 2026. Limits are illustrative and can change. The tool deliberately does not promise that a feature is enabled in a visitor's actual account.

### Decision checks

The rule engine handles standard surveys/forms and existing dashboards as possible native-software solutions even when visitors ask for a public interface. Complex interactive calculators, bespoke portals, and tailored output generators remain candidates for custom development after simpler approaches are evaluated. High-consequence automated decisions receive explicit human-review guidance.

## Regression testing

Run `node --test projects/ai-workflow-decision-navigator/tests/smoke.test.mjs` from the repository root. The dependency-free tests cover the five example decision paths, 29-program catalog count, standard-form versus bespoke-interface routing, a high-consequence guardrail, and required task entry. A scoped GitHub Actions workflow runs the tests on relevant push and pull-request changes.

Browser-specific keyboard, screen-reader, zoom, touch, Firefox/WebKit, and export/clipboard testing remains an independent release requirement; simulated DOM tests do not replace native interaction testing.

## Data and limits

All answers and the decision process remain in the browser. No model calls or account connections are needed. The tool does not inspect installed software, certify compliance, guarantee savings, or perform any recommended action. The privacy checks alert people to verify permissions before sharing sensitive information, connecting systems, or taking consequential actions.

Use the **[working interface](https://www.lauraelizabethhand.com/resources/project-operations-tools/ai-workflow-decision-navigator/)** to try the tool. GitHub's HTML file view displays source code rather than running the interface.

## Capability references

- [Microsoft: Power Query in Excel](https://support.microsoft.com/en-us/excel/about-power-query-in-excel)
- [Microsoft: Power Automate licensing](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/faqs)
- [Google: Sheets macros](https://support.google.com/docs/answer/7665004)
- [Google: Apps Script limits](https://developers.google.com/apps-script/guides/services/quotas)
- [Asana: plan features](https://asana.com/pricing)
- [OpenAI: GPT configuration and availability](https://help.openai.com/en/articles/8554397-creating-a-gpt)
- [Zapier: Free plan features](https://help.zapier.com/hc/en-us/articles/32337438839565-What-s-included-in-Zapier-s-Free-plan)

The implementation is intentionally dependency-free HTML, CSS, and JavaScript so the tool remains accessible without a paid AI API.

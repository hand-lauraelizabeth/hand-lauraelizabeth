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

## Platform coverage

The included reference covers Excel, Word, PowerPoint, Outlook, Google Sheets, Google Docs, Gmail, Google Drive, Asana, Trello, ChatGPT, Gemini, Microsoft Copilot, Power Automate, and Zapier. Platform-specific links open vendor guidance. Features and licensing vary; selecting an app does not assert an entitlement.

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

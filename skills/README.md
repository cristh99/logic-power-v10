# Skills

Este directorio contiene skills de agente en formato Agent Skills: cada skill es una
carpeta cuyo nombre debe coincidir con el campo `name` del frontmatter de su
`SKILL.md` (`skills/logic-power-v10/` ↔ `name: logic-power-v10`).

Para cargarla en ChatGPT, Codex o Claude: sube la carpeta de la skill al entorno del
agente o apunta el agente al archivo `SKILL.md`; `agents/openai.yaml` declara su
interfaz para invocación implícita.

Todos los comandos documentados en `logic-power-v10/SKILL.md` fueron ejecutados el
18-09-2026 con Python 3.12.11 y Node v22.14.0 (TLA+/TLC y Lean no se ejecutaron).

# stata_archive — fryst Stata-pipeline (1183, t.o.m. juni 2026)

Disse 25 `.do`-filene er den opprinnelige Stata-baserte data-prep- og
estimeringspipelinen som kjørte på datauniverset **1183** (rådata på
`W:\7020\`, prosjektfiler på `F:\1183\`), sist kjørt 2026-06-02
(decade-rebinning-runden, se `../../RUN_DECADE_UPDATE.md`).

Hele pipelinen er erstattet av R-scriptene ett nivå opp (`../*.R`), som kjører
på datauniverset **1191** med data t.o.m. 2026m2. Se `../../RUN_1191_UPDATE.md`
og `DESIGN_CHOICES.md` §21.

Filene beholdes uendret som proveniens for resultatene fra 1183-kjøringene
(`from_secure_server/` per juni 2026). De skal ikke vedlikeholdes og vil ikke
kjøre mot 1191-stiene.

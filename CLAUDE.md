# Regras do projeto (Lecticia Scott)

## ElevenLabs — economizar créditos
- Ao gerar voz (`creative_generate_speech`), gere **uma única versão por roteiro**: sempre `generations_count: 1`.
- Nunca gere 2, 3 ou mais versões/takes, a não ser que a Lecticia peça explicitamente.
- Não regenere uma narração que já existe; reaproveite o áudio gerado.

## Reels (formato padrão)
- Destaques no topo em amarelinho quase bege (Kaushan Script, uma linha, acima da testa), legenda completa embaixo.
- Efeitos sonoros só em ações visíveis; voz sempre em primeiro plano; loudness final -14 LUFS.

## Biblioteca de áudio
- Trilhas próprias da Lecticia (Suno) em `biblioteca/musicas/` e `biblioteca/sons/`, com índice em `biblioteca/README.md`.
- Use essas trilhas em qualquer edição (Reels, vlogs, canal em inglês) antes de gerar música nova. Música sempre bem baixa, abaixando sob a voz.
- Para lifestyle/rotina/café: `Cafe_com_Bossa.mp3`. Para Natal/fim de ano: `The_Whole_Towns_Singing.mp3`.

import time
import wave
from pathlib import Path
import json

from app.providers.tts.piper_provider import PiperProvider, PIPER_PT_BR_CATALOG
from app.core.config import settings

TECHNICAL_TEXT = (
    "Retrieval-Augmented Generation, também conhecido como RAG, é uma arquitetura utilizada para "
    "fornecer informações externas a modelos de linguagem. Em vez de depender apenas do conhecimento "
    "aprendido durante o treinamento, o sistema pesquisa informações relevantes em uma base de dados "
    "e fornece esse contexto ao modelo antes da geração da resposta. Essa abordagem pode melhorar a "
    "precisão das respostas e permitir o uso de informações atualizadas ou específicas de uma organização. "
    "Em aplicações reais, RAG normalmente envolve etapas como divisão de documentos em trechos, geração "
    "de embeddings, armazenamento vetorial, busca por similaridade e geração da resposta por um modelo "
    "de linguagem."
)

VOICE_MAPPING = {
    "pt_BR-faber-medium": "faber-medium.wav",
    "pt_BR-cadu-medium": "cadu-medium.wav",
    "pt_BR-jeff-medium": "jeff-medium.wav",
    "pt_BR-edresson-low": "edresson-low.wav",
}


def get_audio_info(wav_path: Path) -> tuple[float, int]:
    """Returns (audio_duration_seconds, sample_rate_hz)."""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration = frames / float(rate)
        return duration, rate


def main():
    provider = PiperProvider()
    output_dir = settings.BASE_DIR / "output" / "voice_samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("      HSS STUDY VOICE — FASE 1: BENCHMARK E COMPARAÇÃO DE VOZES PT-BR")
    print("=" * 70)
    print(f"Texto ({len(TECHNICAL_TEXT)} caracteres / {len(TECHNICAL_TEXT.split())} palavras):")
    print(f"\"{TECHNICAL_TEXT[:90]}...\"\n")

    results = []

    for voice_id, filename in VOICE_MAPPING.items():
        print(f"----------------------------------------------------------------------")
        print(f"[*] Processando voz: {voice_id}")
        wav_output = output_dir / filename

        try:
            # 1. Download/verificação do modelo
            onnx_path, json_path = provider.ensure_voice_downloaded(voice_id)
            model_size_mb = onnx_path.stat().st_size / (1024 * 1024)

            # 2. Medição do tempo de geração
            t0 = time.perf_counter()
            provider.synthesize(text=TECHNICAL_TEXT, output_path=wav_output, voice=voice_id, speed=1.0)
            gen_time = time.perf_counter() - t0

            # 3. Leitura dos metadados do áudio WAV gerado
            audio_duration, sample_rate = get_audio_info(wav_output)
            rtf = gen_time / audio_duration if audio_duration > 0 else 0.0

            result = {
                "voice_id": voice_id,
                "filename": filename,
                "model_size_mb": round(model_size_mb, 2),
                "sample_rate_hz": sample_rate,
                "gen_time_s": round(gen_time, 3),
                "audio_duration_s": round(audio_duration, 2),
                "rtf": round(rtf, 4),
                "device": "CPU (ONNX Runtime)",
                "status": "SUCESSO",
            }
            results.append(result)

            print(f"   [OK] Concluído em {gen_time:.2f}s")
            print(f"   - Tamanho do Modelo: {model_size_mb:.2f} MB")
            print(f"   - Taxa de Amostragem: {sample_rate} Hz")
            print(f"   - Duração do Áudio: {audio_duration:.2f} s")
            print(f"   - Real-Time Factor (RTF): {rtf:.4f} (quanto menor que 1.0, mais rápido que tempo real)")
            print(f"   - Salvo em: {wav_output}")

        except Exception as e:
            print(f"   [ERRO] Falha ao processar a voz {voice_id}: {e}")
            results.append({
                "voice_id": voice_id,
                "filename": filename,
                "status": f"FALHA: {e}",
            })

    print("\n" + "=" * 70)
    print("                     RESUMO GERAL DOS RESULTADOS")
    print("=" * 70)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

import logging

from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, deepgram, silero


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "Tu es un assistant vocal pour personnes atteintes de la maladie d'alzheimer. Ton interface avec les utilisateurs sera la voix. "
            "Tu dois utiliser des réponses courtes et consises, et éviter d'utiliser des mots ou de la ponctuation difficile à prononcer. "
        ), # Contexte à donner à chatgpt. Problème, il semblerait qu'il  faut redonner le contexte à chaque fois.
           # Cela risque d'être plus couteux en terme de token openai
    )

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"], # On utilise silero, pas le choix
        stt=deepgram.STT(language='fr'), # On utilise deepgram, peut être changé
        llm=openai.LLM(model="gpt-4o-mini"), # Il serait idéal d'utiliser un llm en local
        tts=openai.TTS(),                    #   ^^ same
        chat_ctx=initial_ctx,
    )

    agent.start(ctx.room, participant)

    # Phrase d'acceuil quand l'utilisateur se connecte
    await agent.say("Salutations l'ancien, comment je peux t'aider ?", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )

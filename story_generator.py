def create_video(storyboard):
    video_segments = []
    total_duration = 0

    for i, entry in enumerate(storyboard):
        folder = f"./temp_{i}"
        os.makedirs(folder, exist_ok=True)

        # ---------------- AUDIO ----------------
        audio_path = f"audio_{i}.wav"
        tts_client.tts_to_file(
            text=entry["text"],
            file_path=audio_path,
            language="en",
            speaker_wav=SPEAKER_WAV
        )

        audio_clip = AudioFileClip(audio_path)

        if total_duration + audio_clip.duration > MAX_SHORT_DURATION:
            audio_clip = audio_clip.subclip(
                0, MAX_SHORT_DURATION - total_duration
            )

        duration = audio_clip.duration
        total_duration += duration

        clip = None

        # ---------------- KEYWORD STRATEGY ----------------
        primary_kw = entry.get("keyword")
        identity_kw = entry.get("identity_keyword")

        keywords = []
        if primary_kw:
            keywords.append(primary_kw)

        keywords += KEYWORD_FALLBACKS

        # ---------------- VISUAL SELECTION ----------------
        for kw in keywords:
            # 1️⃣ Pixabay video (BEST)
            video_path = download_pixabay_video(kw, folder)
            if video_path:
                clip = normalize_video(video_path, duration)
                break

            # 2️⃣ Pixabay image
            image_path = download_pixabay_image(kw, folder)
            if image_path:
                safe = os.path.join(folder, "safe.jpg")
                normalize_image(image_path, safe)

                # Shorter duration for static images (retention boost)
                img_duration = min(duration, 3.5)

                clip = ImageClip(safe).set_duration(img_duration)
                clip = ken_burns_effect(clip, zoom_factor=1.18)
                break

        # 3️⃣ Google image ONLY for identity keyword
        if not clip and identity_kw:
            google_image = download_google_image(identity_kw, folder)
            if google_image:
                safe = os.path.join(folder, "safe_google.jpg")
                normalize_image(google_image, safe)

                img_duration = min(duration, 3.5)

                clip = ImageClip(safe).set_duration(img_duration)
                clip = ken_burns_effect(clip, zoom_factor=1.2)

        # 4️⃣ Text fallback (LAST RESORT)
        if not clip:
            fallback = create_text_graphic(entry["text"], folder)
            clip = ImageClip(fallback).set_duration(duration)

        clip = clip.set_audio(audio_clip)
        video_segments.append(clip)

        if total_duration >= MAX_SHORT_DURATION:
            break

    if not video_segments:
        raise RuntimeError("No video segments created")

    final = concatenate_videoclips(video_segments, method="compose")
    final.write_videofile(
        "final_video.mp4",
        fps=30,
        codec="libx264",
        audio_codec="aac"
    )

    return "final_video.mp4"

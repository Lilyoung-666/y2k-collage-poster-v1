# Prompt Compiler

Compile analysis into visible, decisive instructions. Do not include internal reasoning, file paths, privacy notes, percentages that do not affect appearance, or the names of supplied style-reference artists.

Do not compile any prompt until both the Pixel Inspection Gate and Reference Generation Gate defined in `SKILL.md` have passed. A text-only description of a source image is never a substitute for either gate.

## Input Labels

Label every image used in the prompt:

- `Image 1 — hero identity and primary cutout`
- `Image 2 — secondary pose or co-hero`
- `Image 3 — prop or environmental fragment`
- `Image 4 — detail crop source`

State must-use status, quality tier, treatment scale, and identity locks. Do not say only “use all references.” Explain each image's visible job. When a weak source is demoted, name the specific edge element or fragment extracted from it instead of asking the model to feature the entire image.

## Compile These Fields

Resolve before writing:

1. Canvas ratio and intended poster use. Obey an explicit user ratio; otherwise choose the ratio from source orientation, crop safety, subject direction, must-use image count, typography, and collage hierarchy.
2. One-sentence future premise: subject, technological condition, spatial situation, and emotional tension.
3. Dominant spatial stage and what visible source cue allows it.
4. Dominant material system, optional accent material, and consistent light/reflection/transparency behavior.
5. Primary and optional supporting style family, including the single subsystem borrowed from the supporting family.
6. Multi-image quality tiers and any source demotion: hero-capable, supporting, or low-quality edge source.
7. Hero, co-hero, echoes, detail crops, interface replay, and texture ghost.
8. Identity and relationship locks.
9. Background, subject field, and annotation field.
10. Dominant overlap, entry point, eye path, and quiet exit.
11. Fidelity, translation, and experimental treatment assignments.
12. Invented motifs and the job and source cue for each motif class.
13. Global palette, contrast, lighting, edge behavior, resolution hierarchy, and reproduction texture.
14. Exact text, type roles, placement, and relative scale.
15. Boundary between source-derived collage elements and invented environment; keep collage construction visible.
16. Hard avoids specific to the selected route and sources.

## Prompt Shape

Write five compact paragraphs or labeled blocks:

### 1. Canvas and hierarchy

Specify the exact ratio, dominant field, hero scale, depth bands, focal entry, dominant overlap, eye path, and quiet exit. If the user supplied a ratio, treat it as locked. If not, select portrait, landscape, or square and a concrete ratio that preserves the sources and best supports the composition; never insert an automatic 4:5 default.

### 2. Source roles and invariants

Assign every input image a role and quality tier. State which face, hair, outfit, pose, prop, object geometry, or multi-person relationship must remain truthful. State which source background fragments may be retained or removed. If a stronger source exists, explicitly prevent a low-pixel or visibly poor source from becoming the Hero, full-bleed field, or overscale crop; describe only the small peripheral fragment extracted from it. If all sources are strong, do not add artificial quality hierarchy.

### 3. Collage operations

Describe which source elements become full cutouts, echoes, detail crops, interface replays, and ghosts. State scale contrast, overlaps, frames, cropping, and which elements sit in front of or behind the hero.

### 4. Future premise, style, material, and type

State the future premise, spatial stage, emotional tension, primary family, and optional supporting subsystem. Describe one dominant material system and make reflection, transparency, glow, shadow, and edges obey it. Name only the motifs selected for this image, the visible source cue and purpose of each class, the unified palette and texture, exact wording, typography roles, and placement. Require source-derived collage seams, frames, cutouts, or repetitions to remain visible so the result does not collapse into seamless sci-fi concept art.

### 5. Fidelity and avoids

Require at least one clear identity-preserving version of each must-use subject. Prohibit extra people, face–body swaps, invented outfits, random motif piles, conflicting styles, generic future scenery, copied logos, watermarks, and route-specific failures.

## Default Text Behavior

- Use supplied text verbatim and quote it in the prompt.
- When no text is supplied, prefer a visual poster with no semantic headline if the image is already dense.
- When text materially strengthens the route, author one English phrase of four words or fewer. Keep it emotional or scene-aware, not factual.
- Add up to three generic micro-labels only when the selected family structurally uses labels, interfaces, transit signals, prototype specifications, or specimen diagnostics. Examples include `ONLINE`, `NOW PLAYING`, `LOADING`, `READY`, `SIGNAL`, or a source-derived one-word mood.
- Do not invent names, dates, credits, releases, locations, quotations, or product claims.

## Generation Invocation

- Reconfirm both hard capability gates before invocation. Every must-use image must appear in both `inspected_image_handles` and `generation_reference_handles`.
- Discover the host's image capabilities before invocation. Use a suitable built-in image-generation or image-editing tool by default, regardless of its vendor or model, when it can consume the required references and return an image.
- Only when no suitable built-in image tool exists, invoke a user-configured third-party Provider through the `image-generation-provider/v1` contract defined in `SKILL.md`. Map the compiled prompt, reference-image roles, must-use flags, canvas ratio, and output format into the adapter; let the adapter handle credentials and Provider-specific parameters.
- In a host that supports local reference paths, inspect them first and pass only the necessary local paths using the host tool's native reference-image field. In Codex-compatible environments this may be `referenced_image_paths`.
- When targets exist only as recent conversation images, use the host's smallest supported recent-image selection that contains every target. In Codex-compatible environments this may be `num_last_images_to_include`.
- Never combine mutually exclusive reference-selection mechanisms in one invocation.
- Never invoke a prompt-only or text-to-image backend for this skill. Translating inspected images into prose does not make a text-only generator reference-conditioned.
- Describe the task as multi-image compositing and style transformation, not as unrelated new scene generation.
- Keep all must-use images included. Exclude optional images only after the Asset Board shows they weaken hierarchy.
- If neither a suitable host tool nor a configured reference-image-capable Provider exists, stop and return only the Reference Generation Gate failure response from `SKILL.md`. Do not return a substitute prompt or generation handoff.

## Inspection Pass

Inspect at normal size for:

- facial and object fidelity;
- correct face, body, outfit, and prop associations;
- text accuracy;
- edge quality and accidental extra anatomy;
- whether source crops remain recognizable;
- whether weak sources remain at a scale supported by their usable detail;
- coherent palette and texture;
- consistent material response, lighting, reflection, and transparency;
- source-responsive architecture, devices, interfaces, or material motifs.

Inspect at thumbnail size for:

- dominant hero;
- source quality and visual prominence are aligned;
- entry point and eye path;
- primary style dominance;
- supporting-style restraint;
- legibility of the future premise and emotional tension;
- spatial-stage coherence without losing collage construction;
- scale contrast and depth;
- density versus readability.

## One-Pass Correction Format

Regenerate at most once using this structure:

```text
Keep unchanged: <successful identity, layout, palette, and style decisions>.
Correct only: <one observed failure>.
Required visible change: <specific pixel-level result>.
Do not introduce: <likely side effects>.
```

Examples:

- `Correct only the hero's identity: restore the supplied face shape, haircut, white top, and original standing pose; keep the collage layout and blue-magenta palette unchanged.`
- `Correct only the style collision: remove chrome bubbles and reflective ribbons; keep the Webcore desktop framing and use Punk Halftone only inside the diagnostic thumbnails.`
- `Correct only the visual clutter: delete half of the small icons, preserve the hero and three source crops, and restore one quiet area around the lower-right type.`
- `Correct only the generic futurism: preserve the hero and layout, replace the stock purple skyline with a cold reflective transit corridor extended from the source railings, and keep the lonely cyan–amber light tension.`
- `Correct only the material incoherence: keep the Liquid Chrome composition, remove flat plastic panels, and make portals, title edges, highlights, and reflections share one coherent liquid-metal behavior.`

## Return

Return only the rendered image, then end. Do not append a creative rationale, style label, summary, process note, or follow-up sentence. Do not expose the Asset Board or full prompt unless explicitly asked.

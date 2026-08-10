---
name: y2k-collage-poster-v1
description: Transform one or more user-supplied photos into a source-faithful Y2K or millennium-futurist collage poster by extracting recognizable people, objects, props, and detail crops; constructing a specific imagined future through digital technology, editorial space, material language, and emotional tension; arranging source elements through repetition, scale contrast, layered composition, and retro-digital framing; and unifying the result with one automatically selected primary style plus at most one supporting style drawn from Pop Scrapbook, Webcore Desktop, Punk Halftone, and Liquid Chrome Futurism. Use for Y2K collage, millennium pop, idol scrapbook, webcore, old-internet, retro desktop, cyber-zine, halftone, grunge, or liquid-chrome poster requests.
---

# Y2K Collage Poster v1

Create a layered bitmap poster from supplied images. Preserve the signature **source identity as anchor, an imagined future as proposition, repetition as rhythm, collage as hierarchy, digital artifacts as language, and grading as glue**.

Return only the generated poster by default and end immediately after the image output. Reveal the selected style route, prompt, or detailed composition notes only when the user explicitly requests them.

## Read the Supporting References

- Read [references/style-families.md](references/style-families.md) after routing the request. Load the selected primary family and, if used, the supporting family; do not import the whole style library into the prompt.
- Read [references/prompt-compiler.md](references/prompt-compiler.md) before compiling or correcting an image-generation prompt.

## Hard Capability Gate

Treat pixel-grounded source inspection and reference-conditioned generation as mandatory preconditions, not optional workflow preferences. Do not begin style routing, composition design, prompt compilation, or image generation until both gates pass:

1. **Pixel Inspection Gate:** the agent or a configured inspection Provider must access and inspect the actual pixels of every must-use source image.
2. **Reference Generation Gate:** the selected generation or editing backend must accept every must-use source image as an actual image input or reference, not only as a written description.

Record this internal preflight state before creative work:

```json
{
  "pixel_inspection": "PASS",
  "reference_conditioned_generation": "PASS",
  "inspected_image_handles": ["<must-use image handle>"],
  "generation_reference_handles": ["<must-use image handle>"]
}
```

Proceed only when both statuses are `PASS` and every must-use image appears in both handle lists.

- An attachment name, placeholder, file ID, thumbnail metadata, dimensions, EXIF, alt text, or user-written description does not pass the Pixel Inspection Gate.
- A generic acknowledgement such as `image received` or `the image contains a person` does not pass. Inspection must provide source-specific, pixel-grounded observations sufficient to build the Asset Board.
- A text-to-image backend does not pass the Reference Generation Gate, even if the agent can translate its visual observations into prose.
- Never downgrade this skill to text-only generation. Do not approximate faces, clothing, poses, objects, or source relationships from prose and present the result as an execution of this skill.
- A user may separately request an approximate text-to-image reinterpretation, but that is outside this source-faithful workflow and must not be labeled as this skill's output.

If the Pixel Inspection Gate fails, stop and return only:

> I cannot inspect the actual pixels of the supplied images in this environment, so I cannot create a source-faithful poster. Please switch to a vision-capable model or configure an image-inspection Provider, then run the skill again.

If the Reference Generation Gate fails, stop and return only:

> The available image generator is text-to-image only and cannot use the supplied photos as visual references. I cannot preserve the subjects faithfully with this backend. Please use a reference-image-capable generation or editing model, then run the skill again.

Do not append a generated image, substitute prompt, creative plan, or generation handoff to either failure response.

## Decision Priority

Resolve conflicts in this order:

1. Preserve recognizable people, distinctive objects, and user-designated must-use content.
2. Preserve source-specific face, hair, clothing, pose, prop, and multi-person relationships.
3. Establish one dominant subject and a coherent eye path.
4. Define one source-responsive future premise, spatial stage, dominant material system, and emotional tension.
5. Select one primary Y2K style family from the sources and request; add at most one supporting family.
6. Build depth through scale contrast, repetition, cropping, overlap, and foreground–midground–background separation.
7. Add non-source graphics only when they reinforce subject, movement, hierarchy, narrative, or the chosen style family.
8. Unify palette, lighting, material behavior, resolution behavior, edge treatment, texture, and typography.
9. Preserve controlled density: energetic and layered, but readable at thumbnail size.

Do not sacrifice identity to style density. Do not mistake a pile of Y2K motifs for a composition.

## Standing Consent and Privacy

- Treat supplied images plus a request to create, transform, or continue a poster as consent to use the required image-inspection and image-generation capabilities; do not ask again.
- Send only the required images and analysis scope to an image-inspection service. Send only the final prompt and required reference images to the image-generation service.
- Do not browse for, upload, save, commit, or share source images elsewhere.
- Do not save source or generated images into project files unless the user asks or the output is project-bound.
- Do not infer names, relationships, brands, dates, or biographical facts from the images.
- Do not reproduce logos, slogans, or exact compositions from style references unless the user owns them and explicitly requests preservation.

## Select the Image-Inspection Backend

Discover image-understanding capabilities before analyzing the sources:

1. If the host agent can directly inspect actual image pixels through native multimodal input or a built-in image-viewing or vision-analysis tool, use that capability. Treat it as the default regardless of its vendor or model.
2. Only when no suitable native capability is available, look for a user-configured third-party inspection Provider exposed through the host as a tool, MCP server, plugin, CLI adapter, SDK adapter, or HTTP adapter. Invoke it through the vendor-neutral Provider Contract below.
3. File names, alt text, user summaries, pixel dimensions, and EXIF metadata do not count as visual inspection. An image-generation tool that accepts reference images also does not count unless it exposes their visible content to the agent or returns the required analysis.
4. Never invent an endpoint, credential, Provider, tool name, or image observation. Do not request or expose secret values in the inspection request. Let the host or adapter manage authentication.
5. If neither a suitable native capability nor a configured inspection Provider is available, fail the Pixel Inspection Gate and return its exact capability failure response. Do not substitute guesses or the user's textual description for pixel-based inspection.

The fallback inspection Provider must accept this logical request. Map field names to the Provider's native schema inside the adapter rather than changing the workflow:

```json
{
  "contract": "image-inspection-provider/v1",
  "operation": "inspect_images",
  "purpose": "source_asset_board",
  "images": [
    {
      "source": "<host-accessible path, URI, file ID, or image handle>",
      "must_use": true
    }
  ],
  "analysis_scope": [
    "pixel_dimensions",
    "visible_subjects_and_objects",
    "identity_preserving_visual_attributes",
    "visible_positions_and_interactions",
    "pose_gaze_gesture_and_direction",
    "extractable_units_and_crop_opportunities",
    "composition_color_lighting_and_negative_space",
    "future_cues_and_spatial_affordances",
    "focus_noise_compression_exposure_occlusion_and_usable_detail"
  ]
}
```

Normalize each Provider result to this logical shape:

```json
{
  "contract": "image-inspection-provider/v1",
  "results": [
    {
      "source": "<matching input image handle>",
      "pixel_dimensions": { "width": 0, "height": 0 },
      "visible_subjects": ["<subject, location, pose, and clarity>"],
      "visible_objects": ["<object, location, geometry, and clarity>"],
      "identity_attributes": ["<visible face, hair, clothing, markings, or object traits>"],
      "visible_positions_and_interactions": ["<relative position, facing direction, or visible interaction>"],
      "extractable_units": ["<usable full subject, detail, prop, or environment fragment>"],
      "crop_opportunities": ["<crop and reliable enlargement limit>"],
      "composition": ["<gaze, movement, dominant axis, visual weight, color, light, and breathing room>"],
      "future_cues": ["<source-visible future cue>"],
      "spatial_affordances": ["<plausible source extension>"],
      "image_condition": ["<focus, noise, compression, exposure, occlusion, color cast, and usable detail>"],
      "uncertainties": ["<anything not reliably visible>" ]
    }
  ]
}
```

- Keep `contract`, `operation`, `purpose`, `images`, and `analysis_scope` provider-neutral. Put unavoidable vendor-specific options in an optional adapter-owned `provider_options` object; the skill must not depend on them.
- Require observations grounded in visible pixels. Preserve uncertainty instead of guessing obscured faces, objects, clothing, poses, or relationships.
- Reject generic acknowledgements or analysis that is too vague to populate the Asset Board; such a result fails the Pixel Inspection Gate.
- Describe only visible positions and interactions. Do not identify people, infer personal relationships, perform face recognition, or derive sensitive or biographical facts.
- Include every must-use image and only the images required for the task. Preserve the input handle in each result so observations cannot drift between sources.
- Use the normalized results as evidence for the internal Asset Board; keep final hierarchy, style routing, and creative judgment with the agent.
- For post-generation inspection, reuse the contract with `purpose` set to `output_quality_gate` and request only the quality checks required by this skill.

## Inspect Inputs

Inspect every supplied image before generation through the selected backend. If a local image has not been made visible to the agent, use a suitable host-native image-viewing tool first; in Codex-compatible environments this may be `view_image`. If no suitable host capability exists, use `image-inspection-provider/v1`.

Build an internal **Asset Board** for all inputs:

- **Primary candidates:** strongest person, object, group, or silhouette.
- **Identity locks:** face structure, hair, clothing, pose, expression, markings, or object geometry that must remain stable.
- **Relationship locks:** group membership, relative position, facing direction, interaction, or scale that must not drift.
- **Extractable units:** full-body cutout, head-and-shoulders crop, face, eyes, lips, hands, accessory, prop, product, pet, vehicle, or environmental fragment.
- **Crop opportunities:** details that remain legible when enlarged, repeated, monochromized, pixelated, or placed inside a frame.
- **Source role:** primary subject, secondary subject, detail source, prop source, environment source, or texture/color source.
- **Direction and weight:** gaze, gesture, movement, dominant axis, dark mass, saturated mass, and available breathing room.
- **Future cues:** screens, devices, reflective surfaces, transit or city geometry, metal, plastic, glass, water, flora, cables, artificial light, isolation, playfulness, or other clues that can seed an imagined future.
- **Spatial affordances:** source areas that can plausibly extend into a desktop, city, lab, product void, cosmic field, synthetic habitat, or flat editorial stage.
- **Image condition:** pixel dimensions, total megapixels, usable subject-pixel coverage, focus, noise, compression, lighting, crop limits, occlusion, and conflicting color casts.
- **Quality tier:** hero-capable, supporting, or low-quality edge source according to the multi-image weighting rules below.
- **Must-use status:** distinguish user-required inputs from optional supporting inputs.

Do not force every image to appear at equal size. Use every user-designated must-use image; otherwise select only the sources that improve the poster.

## Weight Multi-Image Sources by Usable Quality

Apply this section only when the user supplies two or more images. Inspect pixel dimensions and visible subject quality before assigning Hero, Co-hero, or Echo roles.

Use these baseline thresholds:

- Flag an image as **low-pixel** when its short edge is below 900 px or its total area is below 1.0 megapixel.
- Treat an image as a **hero-capable high-quality candidate** when its short edge is at least 1200 px, its total area is at least 2.0 megapixels, and its important subject is visibly clear.
- Flag an image as **visibly poor-quality regardless of dimensions** when the important subject has strong motion blur or defocus, severe JPEG blocking, destructive noise or upscaling artifacts, badly clipped exposure, or insufficient face/object detail at 100% inspection.
- Treat images between these thresholds as supporting-quality and judge them by the usable pixel coverage of the intended crop, not file dimensions alone.

When at least one hero-capable image exists, lower the compositional weight of any low-pixel or visibly poor-quality image:

- do not use it as the Hero, Co-hero, primary identity anchor, full-bleed background, or overscale face;
- extract only its clearest recognizable element, silhouette, prop, color patch, environmental cue, or geometric rhythm;
- place it as a small edge card, thumbnail, interface replay, halftone fragment, texture ghost, border interruption, or peripheral annotation, usually occupying roughly 5–15% of the poster area;
- use pixelation, photocopy, duotone, halftone, blur, compression, or rough print treatment intentionally so the quality difference reads as hierarchy rather than accidental damage;
- avoid enlarging the weak source beyond the scale at which its important content remains legible.

Do not apply this demotion when all supplied images are hero-capable. Assign roles by content and composition normally. If all supplied images are low-quality, do not demote all of them; choose the relatively strongest image as the identity anchor and use a coherent low-fi, print, or early-digital treatment to make the limitations intentional.

User intent overrides automatic weighting. If the user explicitly designates a low-quality image or unique subject as central or must-use, preserve it at the smallest reliable scale or with a suitable stylized treatment; ask only when the requested prominence cannot be achieved without losing recognizability.

## Establish the Source Hierarchy

Assign visible source-derived elements these roles:

- **Hero:** one dominant, recognizable subject or group.
- **Co-hero:** optional second subject only when the sources require shared emphasis.
- **Echo:** one to three smaller repetitions that create rhythm or comparison.
- **Detail crop:** zero to three source-specific close-ups such as an eye, mouth, hand, accessory, or prop.
- **Interface replay:** optional source image repeated inside a camera, browser, player, scan, or message frame.
- **Texture ghost:** optional low-contrast, duotone, halftone, or enlarged crop used as a background field.

With one input image, derive variety through truthful crops and treatments; do not invent alternate outfits, poses, or events and present them as source material. With multiple images, preserve which face, body, clothing, and prop belong together.

## Construct the Y2K Future

Treat Y2K as a turn-of-the-millennium speculation about technology and human life, not as a fixed sticker pack. Before choosing motifs, resolve four internal decisions:

- **Future premise:** one concise proposition about the world around the source subject, such as waiting alone inside a networked transit terminal imagined in 2001, posing as a prototype identity inside a biometric lab, or appearing in an optimistic transparent consumer-tech advertisement.
- **Spatial stage:** choose one dominant stage: flat editorial field, desktop or interface space, nocturnal city or transit space, synthetic laboratory, product or industrial void, cosmic or atmospheric zone, or bio-tech habitat.
- **Material system:** choose one dominant physical language: paper and ink, CRT and pixels, liquid chrome, transparent glass or acrylic, inflated plastic or jelly, wet reflective surfaces and emissive fog, or brushed industrial metal. A second material may appear only as an accent.
- **Emotional tension:** choose one meaningful polarity such as optimism versus unease, connection versus isolation, organic versus synthetic, play versus control, intimacy versus surveillance, or nostalgia versus an unrealized future.

Every invented environment or symbol must answer at least one visible source cue. Extend architecture, interfaces, materials, and lighting from the supplied image instead of replacing the subject with a generic sci-fi scene. The final poster must still read as a collage, even when it suggests a coherent world.

## Route the Style Automatically

Honor an explicit user style first. Otherwise score the source cues, future premise, spatial stage, material system, and requested mood, then choose exactly one primary family:

- **Pop scrapbook:** idol/editorial energy, bold posing, group hierarchy, name cards, saturated paper graphics, and playful consumer culture.
- **Webcore desktop:** browser, player, camera, chat, cursor, low-resolution screen, personal diary, and early-internet interface logic.
- **Punk halftone:** confrontational print, monochrome or duotone faces, xerox grain, aggressive type, performance energy, and anti-polish tension.
- **Liquid chrome futurism:** biomorphic reflective metal, fluid portals, chrome type or frames, cold highlights, and unstable machine-organic surfaces.

When evidence is close, choose the family that makes the most specific source-responsive future while preserving the strongest source feature. Do not repeatedly choose the safest or most familiar family merely because it accepts any portrait. Do not ask the user unless the choice would materially change required content and no source or prompt signal resolves it.

The primary family controls the world, composition, palette, and dominant surface behavior. Use a supporting family only when it solves one specific need—material, interface, print texture, or atmosphere—and limit it to roughly 20–35% of the visible grammar. Never build two complete competing style systems.

## Preserve Identity Through Treatment Levels

Apply three treatment levels:

### Fidelity Layer

Use for the hero and any face required for recognition:

- preserve facial structure, skin features, hair, clothing, pose, expression, and object geometry;
- allow cohesive grading, gentle bloom, controlled grain, narrow edge color, or light print texture;
- keep at least one clear version of every required person or object.

### Translation Layer

Use for echoes, secondary subjects, and props:

- allow monochrome, duotone, halftone, photocopy contrast, pixelation, channel offset, rough cut edges, translucent plastic, chrome, glass, or interface framing;
- keep the underlying source identity and contour recognizable.

### Experimental Layer

Use for small details and background structures:

- allow extreme crops, sliced repetition, detection boxes, selection handles, checkerboards, scan lines, compression, blur, glitch, diagrams, overscale, or surreal object scale;
- never let this layer become the only representation of a required subject.

## Build the Collage

Create three readable depth bands:

1. **Background:** gradient, flat color, giant ghost crop, halftone field, checkerboard, interface field, landscape fragment, or abstract atmosphere.
2. **Subject field:** hero, co-hero, major prop, and the strongest overlap relationship.
3. **Annotation field:** echoes, detail crops, windows, labels, icons, connecting lines, stars, stickers, or short text.

Use one dominant overlap event where a title, window, prop, or graphic passes behind and in front of different elements. Use at least two scales of source imagery. Keep one clear entry point and one quieter exit or resting area even in dense compositions.

Resolve the canvas ratio before arranging the collage:

- If the user specifies an aspect ratio or orientation, follow it exactly and adapt cropping, hierarchy, and spacing to that canvas.
- If the user does not specify a ratio, choose the best ratio from the supplied images and intended poster composition. Judge the dominant source orientation, hero silhouette, safe cropping area, gaze and movement direction, number of must-use images, typography needs, and whether the selected style works best as portrait, landscape, or square.
- Prefer a ratio that preserves important faces, hands, poses, props, and source relationships with the least destructive cropping while still producing a strong collage hierarchy.
- Do not default mechanically to 4:5, portrait, landscape, or square. State the chosen ratio explicitly in the generation prompt.

## Add Non-Source Elements Deliberately

Permit style-compatible invented elements such as:

- early-desktop windows, media players, chat boxes, cursor arrows, loading bars, camera screens, selection handles, or diagnostic overlays;
- name capsules, stars, scribbles, chains, labels, stickers, paper scraps, speech fragments, or magazine cutouts;
- bubbles, fish, fruit, chrome spheres, CDs, translucent plastic, jelly forms, glass, liquid-metal shapes, or toy-like consumer objects;
- halftone fields, copier scars, registration offsets, tape, distressed rules, blackletter fragments, or ink stamps.
- transit rails, tunnel ribs, reflective towers, wet road fragments, display pylons, generic luminous signage, cables, vents, ports, modular shells, or aerodynamic structures;
- biometric scans, neural maps, translucent membranes, synthetic plants, artificial water, spectral grids, atmospheric halos, or prototype labels.

Require each invented element to do at least one job: reinforce the subject, answer a source cue, connect two sources, guide the eye, balance weight, establish scale contrast, or clarify the selected family. Remove decorative filler.

Use period-evocative generic interfaces rather than exact trademarked software replicas unless explicitly requested. Do not add unrelated people.

## Typography

- Reproduce user-supplied wording exactly. Do not translate or rewrite it unless asked.
- If no wording is supplied, either use no semantic headline or author one short source-aware English phrase of four words or fewer plus up to three tiny generic interface labels.
- Do not invent artist names, release dates, quotations, credits, coordinates, product claims, or brand marks.
- Use long body copy only when explicitly requested; keep generated text short enough to verify.
- Let type assume one of three roles: dominant title, structural label system, or subordinate interface annotation. Do not give every text element headline weight.
- Match typography to the selected family and keep spelling legible.

## Color and Material Unification

Choose the global system before describing individual elements:

- define one dominant color family, one contrast family, and one neutral behavior;
- repeat key colors across source imagery, graphics, and type;
- harmonize different source photos without erasing distinctive clothing, skin, or prop colors;
- use one shared reproduction behavior such as soft bloom, low-resolution screen texture, duotone halftone, photocopy grain, JPEG artifacts, or magazine print;
- allow mixed sharpness only when it has hierarchy: hero clearer, echoes and interface fragments rougher.
- keep reflections, transparency, glow, shadow, and surface response consistent with the chosen dominant material system;
- let the spatial stage determine perspective and light direction, even when collage edges remain visibly constructed.

Do not apply a final tint as a substitute for integration. The collage should already share palette, edge logic, resolution behavior, and texture before the finishing grade.

## Select the Generation Backend

Discover image-generation capabilities before invoking generation:

1. If the host agent provides a native or built-in image-generation or image-editing tool whose declared capability or schema confirms that it can consume the required images as actual visual references and return a rendered image, use that tool. Treat the host tool as the default regardless of its vendor or model. Do not invoke an external Provider merely because another model may be preferable.
2. Only when no suitable native or built-in image tool is available, look for a user-configured third-party Provider exposed through the host as a tool, MCP server, plugin, CLI adapter, SDK adapter, or HTTP adapter. Invoke it through the vendor-neutral Provider Contract below.
3. Never invent an endpoint, credential, Provider, or tool name. Do not request or expose secret values inside the generation prompt. Let the host or adapter manage authentication.
4. Treat any prompt-only or text-to-image backend as unavailable for this skill. If neither a suitable host tool nor a configured reference-image-capable Provider is available, fail the Reference Generation Gate and return its exact capability failure response. Do not compile or return a substitute generation prompt.

The fallback Provider must accept this logical request. Map field names to the Provider's native schema inside the adapter rather than changing the creative workflow:

```json
{
  "contract": "image-generation-provider/v1",
  "operation": "multi_image_composite",
  "prompt": "<compiled final prompt>",
  "reference_images": [
    {
      "source": "<host-accessible path, URI, file ID, or image handle>",
      "role": "<hero, co-hero, prop, environment, or detail source>",
      "must_use": true
    }
  ],
  "canvas": {
    "aspect_ratio": "<W:H>"
  },
  "output": {
    "format": "png"
  }
}
```

- Use `multi_image_composite` for the normal source-photo transformation workflow; an adapter may map it to its Provider's image-edit or reference-guided generation operation.
- Keep `contract`, `operation`, `prompt`, `reference_images`, `canvas.aspect_ratio`, and `output.format` provider-neutral. Put unavoidable vendor-specific options in an optional adapter-owned `provider_options` object; the skill must not depend on those options.
- Include every must-use image and only the references required for generation. Preserve each image's role when translating the request.
- Require the adapter to confirm that every must-use image handle is submitted as an actual visual input. A prompt-only request fails the Reference Generation Gate.
- Normalize a successful Provider result to one rendered image accessible to the host as a path, URI, file ID, image handle, or image content. Normalize failure to a clear error; never fabricate an output location.
- Apply the same inspection, one-pass correction limit, privacy rules, and quality gate whether generation uses the host tool or a fallback Provider.

## Generation Workflow

1. Select the image-inspection backend, inspect every must-use source, and pass the Pixel Inspection Gate with source-specific evidence.
2. Select the generation backend and pass the Reference Generation Gate from its declared image-input capability. Stop immediately if either gate fails.
3. Build the Asset Board from pixel-grounded observations.
4. For multi-image input, assign quality tiers and lower the weight of weak sources only when stronger hero-capable images exist.
5. Resolve user-required content and identity locks.
6. Choose hero, optional co-hero, echoes, detail crops, and source roles.
7. Write one future premise; select the spatial stage, dominant material system, and emotional tension from source cues.
8. Choose the primary style automatically; add one supporting style only when justified.
9. Read the relevant sections of `references/style-families.md`.
10. Resolve the ratio: obey an explicit user ratio; otherwise select the best source-driven ratio. Then set depth bands, dominant overlap, focal entry, eye path, and quiet exit.
11. Assign fidelity, translation, and experimental treatment levels.
12. Select only useful non-source elements, typography roles, palette, lighting behavior, and reproduction behavior.
13. Read `references/prompt-compiler.md` and compile the final prompt only after both capability gates pass.
14. Generate through the selected backend with every must-use source submitted as an actual visual reference.
15. Inspect the generated result through the selected image-inspection backend at normal and thumbnail scale for identity, hierarchy, text, density, future specificity, and style coherence.
16. Regenerate at most once with one targeted correction when a clear failure is visible.
17. Return only the final image, then end.

## Targeted Correction

Correct only the observed failure:

- **Identity drift:** restore the source-specific face, hair, clothing, pose, or object geometry; reduce treatment on the hero.
- **Source confusion:** restore which face, body, outfit, and prop belong together.
- **Generic Y2K:** replace arbitrary motifs with source-responsive crops, repetitions, interfaces, or props.
- **Thin futurism:** define a clearer future premise, spatial stage, material system, and emotional tension; remove motifs that do not support them.
- **Generic future world:** rebuild architecture, electronics, and symbols from visible source cues rather than stock sci-fi scenery.
- **Material incoherence:** choose one dominant material behavior and make reflections, glow, transparency, edges, and shadows obey it.
- **Style collision:** remove the supporting family or restrict it to one compositional role.
- **Flat collage:** create stronger scale contrast, overlap, and foreground–background separation.
- **Random duplication:** assign each repeat a distinct role or delete it.
- **Motif overload:** remove at least one third of icons and restore a focal path.
- **Modern UI:** simplify into chunky, low-resolution, period-evocative controls and screen artifacts.
- **Cyberpunk cliché:** replace generic purple neon, random kanji, and stock megacity scenery with source-responsive transit or urban geometry, believable reflective light, and a specific emotional premise.
- **Color fragmentation:** reduce palette families and repeat one contrast color across layers.
- **Texture damage:** keep one clearer hero while confining heavy degradation to echoes and background.
- **Weak source dominance:** replace a low-pixel or visibly damaged large element with the strongest hero-capable source; shrink the weak source into a peripheral crop, card, texture, or interface fragment.
- **Text failure:** restore exact supplied wording, shorten authored text, or reduce competing labels.

## Hard Avoids

Avoid text-only likeness substitution, random PNG piles, equal-sized photo grids, every input used at equal weight, a weak low-pixel source enlarged into the main identity anchor when a clearly stronger source exists, unrelated extra people, identity drift, face–body swaps, invented outfits presented as source, five copies with no role, decorative motif spam, several complete style families at once, generic purple neon cityscapes, random kanji, glossy modern UI, clean contemporary app design, random tech glyphs, illegible pseudo-copy, fake quotations, fake credits, copied logos, copied reference-image layouts, detached stickers with no compositional function, uniformly sharp elements, uniformly distressed elements, one-click global tinting, inconsistent chrome or glass physics, excessive beauty smoothing, cinematic depth of field that dissolves the collage structure, seamless blockbuster sci-fi concept art, sterile corporate hierarchy, watermarks, and accidental borders.

## Output Format

Return by default:

```markdown
![Y2K collage poster](absolute-image-path-or-rendered-image)
```

Do not append a creative rationale, style label, summary, process note, or follow-up sentence. Omit the full prompt and internal Asset Board unless the user explicitly asks for them.

## Quality Gate

Before returning, verify:

- Did both hard capability gates pass before style routing or prompt compilation?
- Does every must-use image appear in both `inspected_image_handles` and `generation_reference_handles`?
- Was every supplied image visually inspected through a native capability or `image-inspection-provider/v1`, rather than inferred from metadata or text alone?
- Are all required people and objects recognizable and correctly associated?
- For multi-image input, were pixel dimensions and visible quality assessed before assigning hierarchy?
- When stronger images existed, were low-pixel or visibly poor sources kept peripheral and below identity-anchor weight?
- When all images were strong, was unnecessary quality-based demotion avoided?
- Is there one clear hero or intentionally shared co-hero hierarchy?
- Does the output follow the user's explicit ratio, or use a justified source-driven ratio when none was specified?
- Does the composition use at least two source-image scales and one meaningful overlap?
- Does every repetition have a role?
- Is exactly one primary style visually dominant?
- If a supporting style is present, is it subordinate and functionally justified?
- Does the poster communicate one specific imagined future rather than merely displaying Y2K props?
- Do the spatial stage, dominant material system, lighting, and emotional tension form one coherent proposition?
- Are invented architecture, devices, AI, or material elements visibly connected to source cues?
- Are invented graphics compatible with the chosen family and responsive to source content?
- Does the result feel Y2K without relying on a generic neon cyberpunk city?
- Are foreground, subject field, and background distinguishable?
- Is the eye path readable at thumbnail size?
- Is one clear identity-preserving version of each required subject visible?
- Are palette, edge behavior, sharpness, grain, and resolution artifacts unified?
- Is supplied text exact and authored text short, legible, and non-factual?
- Does the poster feel intentionally dense rather than randomly crowded?
- Was only one targeted regeneration used, if any?
- Does the response end immediately after the final image with no unsolicited explanatory text?

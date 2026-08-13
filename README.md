# Y2K Collage Poster

Transform one or more photos into layered Y2K and millennium-futurist collage posters.

This skill preserves recognizable people, clothing, poses, objects, and relationships while reinterpreting the source material through bold cropping, repetition, scale contrast, retro-digital framing, expressive typography, and imagined turn-of-the-millennium futures.

## Features

- Works with one or multiple source photos
- Preserves recognizable faces, hairstyles, outfits, poses, props, and objects
- Automatically evaluates image quality and builds a clear visual hierarchy
- Uses repetition, detail crops, interface frames, texture, and scale contrast
- Selects a suitable aspect ratio when none is specified
- Supports exact user-supplied poster text
- Builds each poster around a source-responsive future premise, spatial stage, material system, and emotional tension
- Selects exactly one primary style and uses at most one supporting style for a limited subsystem
- Keeps layered compositions readable at thumbnail size
- Checks identity, hierarchy, typography, color, and style consistency before returning the result

## Style Families

The skill selects one primary style based on the supplied images and requested mood.

### Pop Scrapbook

Colorful editorial collage, bold posing, paper graphics, portrait cards, labels, and playful pop energy.

### Webcore Desktop

Early-internet interfaces, browser windows, media players, cursors, pixel textures, and personal digital-diary aesthetics.

### Punk Halftone

Xerox grain, coarse halftones, duotone portraits, distressed typography, and confrontational print-zine energy.

### Liquid Chrome Futurism

Reflective metal, fluid chrome forms, cold highlights, glass accents, and machine-organic futuristic surfaces.

### Techno Pop Campaign

Turn-of-the-millennium consumer-tech advertising built around a clear promotional hero, oversized source-responsive gadgets or product structures, saturated campaign color, hard-flash portrait treatment, translucent plastic, early-digital compositing, and game-cover or product-mark typography.

In addition, a supporting style may be added only when it solves one specific compositional need, such as a contained interface replay, print texture, editorial card system, or restrained material accent. The primary style continues to control the world, composition, palette, typography, and dominant surface behavior.

## Installation

Download or clone this repository, then copy the `y2k-collage-poster-v1` folder into the skills directory supported by your agent.

For Codex, the default personal skills directory is:

```text
~/.codex/skills/
```

Restart or reload your agent if required.

## Capability Requirements

Before running the skill, confirm that the selected model or agent environment can both inspect the actual pixels of the supplied images and generate or edit an image while using those source images as real visual references. A model that can only read text, or a generator that can only create an image from a written description, is not sufficient for this source-faithful workflow.

The skill enforces two hard capability gates before any style routing, composition planning, prompt compilation, or image generation begins:

1. **Pixel Inspection Gate:** the agent or a configured inspection Provider must inspect the actual pixels of every must-use source image and return source-specific visual observations.
2. **Reference Generation Gate:** the generation or editing backend must accept every must-use source image as an actual image input or visual reference, rather than relying only on a text description.

If either gate fails, the skill stops instead of approximating the supplied people, clothing, poses, objects, or relationships through text-only generation.

## Usage

Supply one or more photos and ask your agent to use the skill.

### Basic Example

```text
Use y2k-collage-poster-v1 to transform these photos into a Y2K collage poster.
```

### Directed Example

```text
Use y2k-collage-poster-v1 to create a 3:4 vertical Webcore poster.

Use the first photo as the main subject and the other photos as smaller
repeated frames. Preserve the subject's face, hairstyle, clothing, and
headphones. Use silver, icy blue, and acid green.

The title must read: "SIGNAL LOST"
```

You may specify:

- Aspect ratio or orientation
- Primary and must-use photos
- Preferred style family
- A supporting style for one limited subsystem
- Color palette
- Exact poster text
- Important facial, clothing, pose, or object details

If these choices are omitted, the skill determines them from the supplied images.

### Recommended Workflow

For best results, start by giving the source images directly to the agent with a simple request. Let the agent inspect the images and determine the strongest subject, visual hierarchy, future premise, spatial stage, style route, palette, material system, emotional tension, and composition from the source itself.

Choose images in which the main person or subject is clear, sufficiently large, and reasonably well focused. When supplying multiple images, try to use sources with broadly compatible color palettes, lighting, contrast, and photographic styles. They do not need to match perfectly, but extremely different sources can make the final collage harder to unify.

Add only the constraints that genuinely matter, such as a required aspect ratio, must-use image, or exact poster text. Stacking too many style tags, motifs, colors, layout instructions, and decorative requirements can create prompt pollution, weaken source fidelity, and make the final composition less coherent.

## Creative Approach

Each poster is built around:

1. A recognizable source identity
2. A clear visual hierarchy
3. A source-responsive future premise
4. One dominant spatial stage
5. One dominant material and color system
6. A meaningful emotional tension
7. Repetition, cropping, overlap, and scale contrast
8. A readable path through the composition

The result remains visibly constructed as a collage instead of becoming a generic science-fiction scene.

## Image Handling

The skill inspects the actual pixels of every supplied image before generation and builds an internal Asset Board covering visible subjects and objects, identity and relationship locks, extractable units, crop opportunities, composition, future cues, spatial affordances, image condition, source role, and must-use status.

With multiple sources, the skill evaluates pixel dimensions and usable visual detail before assigning hierarchy. Stronger images may become the Hero or Co-hero, while lower-resolution or visibly damaged images may appear as smaller edge cards, halftone fragments, interface replays, texture ghosts, or peripheral annotations. User-designated must-use images are preserved at a scale supported by their recognizable detail.

With a single source image, the skill creates variety through truthful crops and visual treatments. It does not invent alternate outfits, poses, or events and present them as source material.

Source-derived elements are assigned to three treatment levels: a clear Fidelity Layer for identity anchors, a more stylized Translation Layer for echoes and secondary elements, and an Experimental Layer for small crops, glitches, scan lines, diagrams, or background structures. Every required subject retains at least one recognizable representation.

The skill does not infer personal names, relationships, locations, brands, dates, or biographical information from supplied images.

## Requirements

A compatible agent with:

- Support for loading skill instructions
- Pixel-level access to the supplied images through a vision-capable model, tool, or inspection Provider
- Reference-image-capable generation or editing, with the supplied photos accepted as actual visual inputs

## Standalone Python Runner

The repository also includes `scripts/y2k_collage_provider_runner.py`, a standalone implementation of the same source-faithful Y2K collage workflow. It can inspect sources, build the creative plan, invoke compatible image Providers, validate the rendered poster, and apply at most one targeted correction without requiring the skill documents at runtime.

The inspection and generation Providers must be connected through the local JSON adapter contracts defined by the script. Because different Providers use different native API formats, the runner does not guess or automatically translate arbitrary API schemas.

Run the following command to print the request format and complete adapter contract information:

```bash
python scripts/y2k_collage_provider_runner.py protocol
```

## Output

By default, the skill returns only the finished poster.

Ask explicitly if you also want the selected style, creative direction, composition notes, or generation prompt.

## Important Note

This skill provides a structured workflow for source-image analysis, visual hierarchy, style selection, prompt compilation, and output inspection. However, it does not guarantee the quality of the final generated image.

The actual result depends heavily on the model or image-generation backend selected by the user, including its ability to understand reference images, preserve people and objects, combine multiple images, render accurate text, support high-resolution output, and follow complex composition and style instructions. Even with the same source images and request, different models may produce significantly different results.

For best results, use a model that supports visual understanding, reference-conditioned generation, multiple image inputs, and high-quality image editing. The clarity, composition, lighting, and usable detail of the source images will also affect the final output. This skill can help the model approach the task in a more structured way, but it cannot overcome the inherent capabilities or limitations of the selected model.

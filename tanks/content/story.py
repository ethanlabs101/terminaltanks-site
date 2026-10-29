"""The story script: one-time whispers, and the Martyr's intro, between-phase lines and outro."""
from __future__ import annotations


STORY_LINES = {          # one-time whispers from an unseen voice (the Martyr, never named): heard once, remembered in the save
    "first_battle": ("That firing angle... I have not seen it in an age.",),
    "master": ("You carry old iron into a new war. Perhaps that is why you survived.",),
    "alien": ("Another world, another hunger. Why must scarcity always end in conquest?",),
    "mothership": ("You have ended a war that was not yours to inherit.", "There is another, older war waiting beneath your feet."),
    "hoarders": ("Ten prisons opened. Ten old sins answered for. And still, you stand.",
                 "Steady hands. Stubborn aim. I knew them once. They run in the blood."),
}

NARRATOR, MARTYR = "NARRATOR", "THE MARTYR"           # who speaks a line of the script
MARTYR_INTRO = [
    (NARRATOR, "Ten vaults opened. Ten ancient hoarders fell. The last seal shatters... and the world holds its breath.", "artifact", False),
    (NARRATOR, "In your hands, the Martyr's Arcane Time Machine begins to hum. Its sand has been falling for ten thousand years.", "artifact", False),
    (NARRATOR, "Then the sand stops.", "awake", True),
    (MARTYR, "So. The last of the Hoarders is beaten.", "mage", False),
    (MARTYR, "I felt every seal break. Each one was a thread of my own life, pulled tight for ten thousand years... and finally cut.", "mage", False),
    (MARTYR, "Do not be afraid, child. I am the one the legends say died sealing the Hoarders away.", "mage", False),
    (MARTYR, "The legends are half right. The world believed I gave my life to bind them. In truth, I bound them... and then I bound myself.", "mage", False),
    (MARTYR, "No mortal body can hold that much magic and live. So I tore myself out of the flow of time, one heartbeat folded inside this hourglass. I did not die. I became the sand.", "mage", False),
    (MARTYR, "I could never step out. Had I stayed human, the power I carried would have burned me to ash before the first century ended. So I waited, inside the artifact, until someone worthy broke the last seal.", "mage", False),
    (MARTYR, "You fought well. You and that tank. You saved the universe. Peace has returned to the people, and their sanctuary stands. Because of you.", "mage", False),
    (MARTYR, "Tell me... that rusted tank you started with. The five hulls, the five shells. Did you ever wonder where they came from?", "mage", False),
    (MARTYR, "Spoils of the first crisis. I handed them down myself, parent to child, for a thousand generations, until they reached you. Old rusty heirlooms.", "mage", False),
    (MARTYR, "I am your many-times-great-grandfather. Everything you are, I set in motion.", "mage", True),
    (MARTYR, "So there is only one thing left to ask of a living legend. Duel me.", "duel", False),
    (MARTYR, "Not for the universe. For the truth. Are you stronger than the one who saved it before you?", "duel", False),
    (MARTYR, "Hold nothing back. I will not.", "duel", True),
]
MARTYR_PHASE0 = [
    (NARRATOR, "PHASE I.  THE EMBER SANCTUM.", "map0", True),
    (MARTYR, "Let us begin where all power begins: fire, and the stone it forges. Wait one turn, and your special strikes for triple. Use it.", "map0", False),
]
MARTYR_BETWEEN = {
    1: [(MARTYR, "Hah! Good. The mountain bows to you.", "map0", False),
        (NARRATOR, "PHASE II.  THE TEMPEST SPIRES.", "map1", True),
        (MARTYR, "Now the sky itself. Wind to carry the shot, water to drown it. Let us see you stand.", "map1", False)],
    2: [(MARTYR, "Wind and water, tamed. You are better than I dreamed.", "map1", False),
        (NARRATOR, "PHASE III.  THE ASTRAL RIFT.", "map2", True),
        (MARTYR, "Then I will stop holding back. Light and dark. The end of time itself. Come, descendant. Show me everything.", "map2", False)],
}
MARTYR_OUTRO = [
    (MARTYR, "...Magnificent.", "win", False),
    (MARTYR, "Ten thousand years I waited. I thought I was waiting to be saved. I was waiting for you.", "win", False),
    (MARTYR, "Take the relics of all six elements. Take the sanctuaries where we fought. They were always meant for the one who got this far.", "win", True),
    (MARTYR, "Carry them well, little one. And do not let the sand run out.", "win", False),
    (MARTYR, "One last thing. What is left of my power cannot follow me into rest... so I give it to you.", "win", False),
    (NARRATOR, "The last of the Martyr's power folds into a single shell of gold and starlight: MARTYR'S BLESSING.", "win", True),
    (MARTYR, "Load it, and nothing that stands in your path will stand for long. Use it well, descendant.", "win", False),
    (NARRATOR, "The hourglass turns one last time. The Martyr rests.", "win", True),
]

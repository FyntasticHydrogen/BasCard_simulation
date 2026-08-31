import os
import pygame
from basys3_simulator.gui import Basys3GUI

def test_gui_headless_render():
    os.environ["HEADLESS"] = "1"
    os.environ["SDL_VIDEODRIVER"] = "dummy"

    gui = Basys3GUI()
    gui.draw()
    assert gui.screen is not None

    # Test clicking a switch SW0
    sw0_rect = gui.sw_rects["SW0"]
    gui.handle_click((sw0_rect.x + 2, sw0_rect.y + 2))
    assert gui.engine.inputs["SW0"] == 1

    gui.draw()

    # Test 7-Segment segment activation
    gui.engine.outputs["AN0"] = 0 # Active low ON
    gui.engine.outputs["CA"] = 0  # Active low Segment A ON
    gui.draw()

    print("GUI Headless integration test passed!")

if __name__ == "__main__":
    test_gui_headless_render()

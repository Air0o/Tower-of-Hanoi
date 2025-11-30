import argparse
import pygame

# ---------------------------
# Configurable parameters
# ---------------------------
pygame.init()
info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h

WINDOW_WIDTH = screen_width#1920
WINDOW_HEIGHT = screen_height#1080
MARGIN = 100

BACKGROUND_COLOR = (24, 26, 27)
PEG_COLOR = (210, 210, 210)
BASE_COLOR = (180, 180, 180)
TEXT_COLOR = (230, 230, 230)

# Disk appearance
DISK_MIN_WIDTH = 70
DISK_MAX_WIDTH = 240
DISK_HEIGHT = 20
DISK_COLORS = [
    (244, 67, 54), (33, 150, 243), (76, 175, 80), (255, 235, 59),
    (156, 39, 176), (255, 152, 0), (0, 188, 212), (121, 85, 72),
    (139, 195, 74), (63, 81, 181), (0, 150, 136), (205, 220, 57)
]

# Animation settings
FPS = 60
LIFT_HEIGHT = 160            # pixels above the stack during the carry
H_SPEED = 24                  # horizontal speed (px/frame)
V_SPEED = 28                 # vertical speed (px/frame)
POST_MOVE_PAUSE_MS = 150     # pause after each placement (milliseconds)

# Peg layout
PEG_COUNT = 3
PEG_WIDTH = 10
BASE_HEIGHT = 12


# ---------------------------
# Data structures
# ---------------------------
class Disk:
    def __init__(self, size_index, total_disks):
        # Size scales linearly between min and max based on index
        t = size_index / (total_disks - 1) if total_disks > 1 else 0
        self.width = int(DISK_MIN_WIDTH + t * (DISK_MAX_WIDTH - DISK_MIN_WIDTH))
        self.height = DISK_HEIGHT
        # Pick color cyclically for > len(DISK_COLORS)
        self.color = DISK_COLORS[size_index % len(DISK_COLORS)]


class Peg:
    def __init__(self, x, base_y):
        self.x = x
        self.base_y = base_y
        self.stack = []  # list of Disk, bottom at index 0


# ---------------------------
# Tower of Hanoi move generator
# ---------------------------
def hanoi_moves(n, src, aux, dst):
    """
    Yield moves as tuples (src_index, dst_index) for n disks
    from peg src to peg dst using aux.
    Peg indices must be distinct and in [0, 2].
    """
    if n <= 0:
        return
    yield from hanoi_moves(n - 1, src, dst, aux)
    yield src, dst
    yield from hanoi_moves(n - 1, aux, src, dst)


# ---------------------------
# Geometry helpers
# ---------------------------
def disk_position(peg: Peg, disk_index_in_stack: int, disk_width: int):
    """
    Compute the (center_x, top_y) position for a disk by its stack index.
    """
    cx = peg.x
    # Top y for this disk: baseline minus base height minus disk heights
    top_y = peg.base_y - BASE_HEIGHT - (disk_index_in_stack + 1) * DISK_HEIGHT
    # Return top-left x of rect (for drawing convenience) from center
    left_x = cx - disk_width // 2
    return left_x, top_y


def peg_positions(width, margin, count):
    """
    Return x positions for 'count' pegs, evenly spaced.
    """
    usable = width - 2 * margin
    spacing = usable // (count - 1)
    return [margin + i * spacing for i in range(count)]


# ---------------------------
# Drawing
# ---------------------------
def draw_scene(screen, pegs, font, move_counter):
    screen.fill(BACKGROUND_COLOR)

    # Draw base line
    base_y = pegs[0].base_y
    pygame.draw.rect(screen, BASE_COLOR, (MARGIN, base_y, WINDOW_WIDTH - 2 * MARGIN, BASE_HEIGHT))

    # Draw pegs
    for peg in pegs:
        pygame.draw.rect(screen, PEG_COLOR, (peg.x - PEG_WIDTH // 2, base_y - 300, PEG_WIDTH, 300))

    # Draw disks on each peg
    for peg in pegs:
        for idx, disk in enumerate(peg.stack):
            left_x, top_y = disk_position(peg, idx, disk.width)
            pygame.draw.rect(screen, disk.color, (left_x, top_y, disk.width, disk.height), border_radius=6)

    # Draw info text
    info = f"Moves: {move_counter}"
    surf = font.render(info, True, TEXT_COLOR)
    screen.blit(surf, (MARGIN, MARGIN))

    pygame.display.flip()


# ---------------------------
# Animation of single move
# ---------------------------
def animate_move(screen, pegs, font, move_counter, src_idx, dst_idx, clock):
    """
    Animate moving the top disk from pegs[src_idx] to pegs[dst_idx]:
    - Lift vertically to a carry height
    - Move horizontally to destination peg
    - Lower onto destination stack
    """
    src_peg = pegs[src_idx]
    dst_peg = pegs[dst_idx]

    # Pop disk from source stack
    disk = src_peg.stack.pop()

    # Starting position
    current_stack_index = len(src_peg.stack)  # where it was
    left_x, top_y = disk_position(src_peg, current_stack_index, disk.width)

    # Define carry target y
    carry_y = src_peg.base_y - BASE_HEIGHT - 300 - LIFT_HEIGHT  # above peg top

    # Step 1: lift
    x = left_x
    y = top_y
    while y > carry_y:
        y = max(carry_y, y - V_SPEED)
        draw_temporary(screen, pegs, font, move_counter, disk, x, y)
        clock.tick(FPS)

    # Step 2: move horizontally to destination peg center
    dst_left_x_target, _ = disk_position(dst_peg, len(dst_peg.stack), disk.width)
    dst_center_x = dst_peg.x
    # Keep y at carry_y, move towards dst_center_x - width/2
    target_left_x = dst_center_x - disk.width // 2
    while abs(x - target_left_x) > H_SPEED:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
        direction = 1 if target_left_x > x else -1
        x += direction * H_SPEED
        draw_temporary(screen, pegs, font, move_counter, disk, x, y)
        clock.tick(FPS)
    x = target_left_x
    draw_temporary(screen, pegs, font, move_counter, disk, x, y)
    clock.tick(FPS)

    # Step 3: lower down onto destination stack
    _, dst_top_y_target = disk_position(dst_peg, len(dst_peg.stack), disk.width)
    while y < dst_top_y_target:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
        y = min(dst_top_y_target, y + V_SPEED)
        draw_temporary(screen, pegs, font, move_counter, disk, x, y)
        clock.tick(FPS)

    # Place disk onto destination stack
    dst_peg.stack.append(disk)

    # Post-move pause
    pygame.time.delay(POST_MOVE_PAUSE_MS)


def draw_temporary(screen, pegs, font, move_counter, moving_disk, x, y):
    """
    Draw the scene plus the moving disk at (x, y) without committing it to a peg stack.
    """
    screen.fill(BACKGROUND_COLOR)

    # Draw base line and pegs
    base_y = pegs[0].base_y
    pygame.draw.rect(screen, BASE_COLOR, (MARGIN, base_y, WINDOW_WIDTH - 2 * MARGIN, BASE_HEIGHT))

    for peg in pegs:
        pygame.draw.rect(screen, PEG_COLOR, (peg.x - PEG_WIDTH // 2, base_y - 300, PEG_WIDTH, 300))

    # Draw disks currently on pegs
    for peg in pegs:
        for idx, disk in enumerate(peg.stack):
            left_x, top_y = disk_position(peg, idx, disk.width)
            pygame.draw.rect(screen, disk.color, (left_x, top_y, disk.width, disk.height), border_radius=6)

    # Draw moving disk last (on top)
    pygame.draw.rect(screen, moving_disk.color, (x, y, moving_disk.width, moving_disk.height), border_radius=6)

    # Info text
    info = f"Mosse: {move_counter}"
    surf = font.render(info, True, TEXT_COLOR)
    screen.blit(surf, (MARGIN, MARGIN))

    pygame.display.flip()


# ---------------------------
# Main
# ---------------------------
def run(num_disks: int):
    pygame.display.set_caption("Torre di Hanoi animata")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 24)

    # Peg setup
    xs = peg_positions(WINDOW_WIDTH, MARGIN + 40, PEG_COUNT)
    base_y = WINDOW_HEIGHT - MARGIN*2
    pegs = [Peg(x, base_y) for x in xs]

    # Build initial stack on peg 0 (largest at bottom)
    for i in range(num_disks, 0, -1):
        pegs[0].stack.append(Disk(i - 1, num_disks))

    # Precompute moves
    moves = list(hanoi_moves(num_disks, 0, 1, 2))
    total_moves = len(moves)

    move_counter = 0
    running = True

    # Draw initial
    draw_scene(screen, pegs, font, move_counter)

    while running:
        # Basic event handling (close window = quit)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if move_counter < total_moves:
            src, dst = moves[move_counter]
            animate_move(screen, pegs, font, move_counter, src, dst, clock)
            move_counter += 1
            draw_scene(screen, pegs, font, move_counter)
        else:
            # Completed; slow down loop but keep window open until user closes
            running = False
            clock.tick(30)

    #pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description="Animated Tower of Hanoi (Pygame)")
    parser.add_argument("-n", "--num-disks", type=int, default=5, help="Number of starting disks (default: 5)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    max_n = max(1, min(args.num_disks, len(DISK_COLORS) * 2))
    n = 1

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
        run(n)
        n += 1
        n %= max_n+1

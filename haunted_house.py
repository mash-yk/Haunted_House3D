'''
Controls:
Player movement: W,A,S,D, space
Camera Control: Arrow keys
Cheat Mode: C
Switch weapon: X
Reload (gun): L
Highlight outlines: V
Reset game: R
'''
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18

import math
import random
import time

start_time = time.time()

quadric = None

fovY = 60
GRID_LENGTH = 4000
first_person_mode = False

cam_back = 260.0
cam_height = 260.0
cam_yaw_offset = 0.0

man_pos = [0.0, 0.0, 0.0] 
man_angle = 0           
man_speed = 5
jumping = False
jump_velocity = 0
keys_pressed = set()
player_lying = False

damage_cooldown_ms = 700
next_damage_ok_at = 0

def can_take_damage():
    return int((time.time() - start_time) * 1000) >= next_damage_ok_at

def mark_damage_window():
    global next_damage_ok_at
    next_damage_ok_at = int((time.time() - start_time) * 1000) + damage_cooldown_ms

current_weapon = 'gun'

# Gun
magazine_size = 15
gun_ammo = magazine_size
is_reloading = False
reload_duration_ms = 1200
reload_end_time = 0
last_shot_time = 0
shot_cooldown_ms = 140
show_reload_hint_ticks = 0

# Sword
sword_swinging = False
sword_swing_start = 0
sword_swing_duration_ms = 280
sword_range = 155.0
sword_arc_deg = 115.0
sword_boss_damage = 18
sword_length = 90.0
sword_thickness = 4.0

lasers = []
ghosts = []
treasures = []

player_life = 10
score = 0
collision_walls = []
game_over = False
victory = False
boss_fight_active = False

cheat_mode = False

boss_dark_mode = False

highlight_mode = False

teleport_pads = [
    (-200, 200, 40),
    (650, -500, 40),
    (1500, -200, 40),
    (400, -1100, 40),
]
teleport_cooldown_until = 0

traps = []

spawn_zones = [
    (-300, 300, -300, 300),        # Room 1
    (-300, 300, -1200, -600),      # Room 2 #1
    (300, 900, -300, 300),         # Room 2 #2
    (200, 800, -1200, -600),       # Room 3 #1
    (900, 1900, -300, 300),        # Room 3 #2
    (800, 1800, -1200, -600),      # Room 3 #3
    (1800, 2200, -1200, -600),     # Room 3 #4
    (-300, 1700, -600, -300),      # hallway (EW)
    (1400, 1700, -600, -200),      # hallway turn
]

def set_color(r, g, b):
    if boss_dark_mode:
        r, g, b = r * 0.5, g * 0.5, b * 0.5
    if cheat_mode:
        r, g, b = min(1.0, r * 1.4), min(1.0, g * 1.4), min(1.0, b * 1.4)
    glColor3f(r, g, b)

class Boss:
    def __init__(self, x, y, z=0):
        self.pos = [x, y, z]
        self.health = 200
        self.alive = True
        self.hit_cooldown = 0.0
        self.speed = 1.0

    def update(self, player_pos):
        if not (self.alive and boss_fight_active):
            return
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        d = math.hypot(dx, dy)
        if d > 1:
            self.pos[0] += dx / d * self.speed
            self.pos[1] += dy / d * self.speed
        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1

    def take_damage(self, amount):
        if self.hit_cooldown > 0 or not self.alive:
            return
        self.health -= amount
        self.hit_cooldown = 12
        if self.health <= 0:
            self.alive = False
            global victory
            victory = True

    def draw(self):
        if not self.alive:
            return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2] + 90)
        head_radius = 100.0

        # core head
        set_color(0.5, 0.0, 0.0)
        gluSphere(quadric, head_radius, 32, 32)

        # horns
        set_color(1.0, 1.0, 1.0)
        for x_off in (-40, +40):
            glPushMatrix()
            glTranslatef(x_off, 0, head_radius + 50)
            glRotatef(180, 1, 0, 0)
            gluCylinder(quadric, 0.0, 20, 60, 16, 4)
            glPopMatrix()

        # fangs
        for x_off in (-80, +80):
            glPushMatrix()
            glTranslatef(x_off, head_radius * 0.8, head_radius * 0.2)
            glRotatef(75, 1, 0, 0)
            gluCylinder(quadric, 0.0, 10, 30, 12, 4)
            glPopMatrix()

        glPopMatrix()

boss = Boss(2650, -400, 0)

def add_wall(x_center, y_center, width, height):
    xmin = x_center - width / 2
    xmax = x_center + width / 2
    ymin = y_center - height / 2
    ymax = y_center + height / 2
    collision_walls.append((xmin, xmax, ymin, ymax))

def aabb_contains_point(aabb, x, y):
    xmin, xmax, ymin, ymax = aabb
    return (xmin <= x <= xmax) and (ymin <= y <= ymax)

def position_collides(x, y):
    for a in collision_walls:
        if aabb_contains_point(a, x, y):
            return True
    return False

def resolve_move_with_walls(oldx, oldy, newx, newy):
    if not position_collides(newx, newy):
        return newx, newy
    if not position_collides(newx, oldy):
        return newx, oldy
    if not position_collides(oldx, newy):
        return oldx, newy
    return oldx, oldy

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    set_color(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def room1():
    ROOM_SIZE = 300
    GRID_STEP = 40
    WALL_HEIGHT = 200
    WALL_THICK = 5
    DARK_BROWN = (0.15, 0.07, 0.02)
    LIGHT_BROWN = (0.4, 0.2, 0.1)

    # Floor
    glBegin(GL_QUADS)
    for x in range(-ROOM_SIZE, ROOM_SIZE, GRID_STEP):
        for y in range(-ROOM_SIZE, ROOM_SIZE, GRID_STEP):
            noise = (abs(x) % 100) * 0.02 + math.sin(x * 0.05) + math.sin((x + y) * 0.1)
            t = (math.sin(noise) + 1) * 0.5
            r = DARK_BROWN[0] + (LIGHT_BROWN[0] - DARK_BROWN[0]) * t
            g = DARK_BROWN[1] + (LIGHT_BROWN[1] - DARK_BROWN[1]) * t
            b = DARK_BROWN[2] + (LIGHT_BROWN[2] - DARK_BROWN[2]) * t
            set_color(r, g, b)
            glVertex3f(x, y, 0)
            glVertex3f(x + GRID_STEP, y, 0)
            glVertex3f(x + GRID_STEP, y + GRID_STEP, 0)
            glVertex3f(x, y + GRID_STEP, 0)
    glEnd()

    wall_color = (0.30, 0.10, 0.10)
    door_w = 120
    half_w = (2 * ROOM_SIZE - door_w) / 2
    set_color(*wall_color)

    # N
    glPushMatrix()
    glTranslatef(0, ROOM_SIZE, WALL_HEIGHT / 2)
    glScalef(2 * ROOM_SIZE, WALL_THICK, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(0, ROOM_SIZE, 2 * ROOM_SIZE, WALL_THICK)

    # S (split door)
    glPushMatrix()
    glTranslatef(-ROOM_SIZE + half_w / 2, -ROOM_SIZE, WALL_HEIGHT / 2)
    glScalef(half_w, WALL_THICK, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(-ROOM_SIZE + half_w / 2, -ROOM_SIZE, half_w, WALL_THICK)

    glPushMatrix()
    glTranslatef(ROOM_SIZE - half_w / 2, -ROOM_SIZE, WALL_HEIGHT / 2)
    glScalef(half_w, WALL_THICK, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(ROOM_SIZE - half_w / 2, -ROOM_SIZE, half_w, WALL_THICK)

    # E
    glPushMatrix()
    glTranslatef(ROOM_SIZE, 0, WALL_HEIGHT / 2)
    glScalef(WALL_THICK, 2 * ROOM_SIZE, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(ROOM_SIZE, 0, WALL_THICK, 2 * ROOM_SIZE)

    # W
    glPushMatrix()
    glTranslatef(-ROOM_SIZE, 0, WALL_HEIGHT / 2)
    glScalef(WALL_THICK, 2 * ROOM_SIZE, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(-ROOM_SIZE, 0, WALL_THICK, 2 * ROOM_SIZE)

def draw_hallway():
    STEP = 40.0
    DARK = (0.15, 0.07, 0.02)
    LIGHT = (0.40, 0.20, 0.10)
    WALL_HEIGHT = 200.0
    WALL_THICK = 5.0
    wall_color = (0.30, 0.10, 0.10)

    x0, y0 = -300.0, -600.0
    HALL_LEN, HALL_WIDTH = 2500.0, 300.0
    x = x0
    while x < x0 + HALL_LEN:
        y = y0
        while y < y0 + HALL_WIDTH:
            n = (abs(x) % 100) * 0.02 + math.sin(x * 0.05) + math.sin((x + y) * 0.1)
            t = (math.sin(n) + 1) * 0.5
            r = DARK[0] + (LIGHT[0] - DARK[0]) * t
            g = DARK[1] + (LIGHT[1] - DARK[1]) * t
            b = DARK[2] + (LIGHT[2] - DARK[2]) * t
            set_color(r, g, b)
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0)
            glVertex3f(x + STEP, y, 0)
            glVertex3f(x + STEP, y + STEP, 0)
            glVertex3f(x, y + STEP, 0)
            glEnd()
            y += STEP
        x += STEP

    x1, y1 = x0 + HALL_LEN - HALL_WIDTH, y0 + HALL_WIDTH
    NS_LEN, NS_WID = HALL_WIDTH, 600.0
    x = x1
    while x < x1 + NS_LEN:
        y = y1
        while y < y1 + NS_WID:
            n = (abs(x) % 100) * 0.02 + math.sin(x * 0.05) + math.sin((x + y) * 0.1)
            t = (math.sin(n) + 1) * 0.5
            r = DARK[0] + (LIGHT[0] - DARK[0]) * t
            g = DARK[1] + (LIGHT[1] - DARK[1]) * t
            b = DARK[2] + (LIGHT[2] - DARK[2]) * t
            set_color(r, g, b)
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0)
            glVertex3f(x + STEP, y, 0)
            glVertex3f(x + STEP, y + STEP, 0)
            glVertex3f(x, y + STEP, 0)
            glEnd()
            y += STEP
        x += STEP

    set_color(*wall_color)
    glPushMatrix()
    glTranslatef(x0, y0 + HALL_WIDTH / 2, WALL_HEIGHT / 2)
    glScalef(WALL_THICK, HALL_WIDTH, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(x0, y0 + HALL_WIDTH / 2, WALL_THICK, HALL_WIDTH)

    wall_x = x1 + NS_LEN / 2.0
    wall_y = y1 + NS_WID
    glPushMatrix()
    glTranslatef(wall_x, wall_y, WALL_HEIGHT / 2.0)
    glScalef(NS_LEN, WALL_THICK, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()
    add_wall(wall_x, wall_y, NS_LEN, WALL_THICK)

def room2(offset_x=0, offset_y=0, door_side='north', door_center=0, door_width=140.0):
    ROOM = 300
    H = 200
    T = 5
    STEP = 40

    glPushMatrix()
    glTranslatef(offset_x, offset_y, 0)

    DARK = (0.15, 0.07, 0.02)
    LIGHT = (0.4, 0.2, 0.1)
    glBegin(GL_QUADS)
    for x in range(-ROOM, ROOM, STEP):
        for y in range(-ROOM, ROOM, STEP):
            n = (abs(x) % 100) * 0.02 + math.sin(x * 0.05) + math.sin((x + y) * 0.1)
            i = (math.sin(n) + 1) * 0.5
            r = DARK[0] + (LIGHT[0] - DARK[0]) * i
            g = DARK[1] + (LIGHT[1] - DARK[1]) * i
            b = DARK[2] + (LIGHT[2] - DARK[2]) * i
            set_color(r, g, b)
            glVertex3f(x, y, 0)
            glVertex3f(x + STEP, y, 0)
            glVertex3f(x + STEP, y + STEP, 0)
            glVertex3f(x, y + STEP, 0)
    glEnd()

    set_color(0.30, 0.10, 0.10)
    half = (2 * ROOM - door_width) / 2

    def W(tx, ty, sx, sy):
        glPushMatrix()
        glTranslatef(tx, ty, H / 2)
        glScalef(sx, sy, H)
        glutSolidCube(1)
        glPopMatrix()
        add_wall(offset_x + tx, offset_y + ty, sx, sy)

    if door_side == 'north':
        W(door_center - door_width / 2 - half / 2, ROOM, half, T)
        W(door_center + door_width / 2 + half / 2, ROOM, half, T)
    else:
        W(0, ROOM, 2 * ROOM, T)

    if door_side == 'south':
        W(door_center - door_width / 2 - half / 2, -ROOM, half, T)
        W(door_center + door_width / 2 + half / 2, -ROOM, half, T)
    else:
        W(0, -ROOM, 2 * ROOM, T)

    if door_side == 'east':
        W(ROOM, door_center - door_width / 2 - half / 2, T, half)
        W(ROOM, door_center + door_width / 2 + half / 2, T, half)
    else:
        W(ROOM, 0, T, 2 * ROOM)

    if door_side == 'west':
        W(-ROOM, door_center - door_width / 2 - half / 2, T, half)
        W(-ROOM, door_center + door_width / 2 + half / 2, T, half)
    else:
        W(-ROOM, 0, T, 2 * ROOM)

    glPopMatrix()

def room3(offset_x=0, offset_y=0, room_w=380, room_h=300, door_side='west', door_center=0, door_width=140.0):
    H = 200
    T = 5
    STEP = 40
    glPushMatrix()
    glTranslatef(offset_x, offset_y, 0)

    DARK = (0.15, 0.07, 0.02)
    LIGHT = (0.40, 0.20, 0.10)
    glBegin(GL_QUADS)
    for x in range(-room_w, room_w, STEP):
        for y in range(-room_h, room_h, STEP):
            n = (abs(x) % 100) * 0.02 + math.sin(x * 0.05) + math.sin((x + y) * 0.1)
            i = (math.sin(n) + 1) * 0.5
            r = DARK[0] + (LIGHT[0] - DARK[0]) * i
            g = DARK[1] + (LIGHT[1] - DARK[1]) * i
            b = DARK[2] + (LIGHT[2] - DARK[2]) * i
            set_color(r, g, b)
            glVertex3f(x, y, 0)
            glVertex3f(x + STEP, y, 0)
            glVertex3f(x + STEP, y + STEP, 0)
            glVertex3f(x, y + STEP, 0)
    glEnd()

    set_color(0.30, 0.10, 0.10)
    half_x = (2 * room_w - door_width) / 2
    half_y = (2 * room_h - door_width) / 2

    def W(tx, ty, sx, sy):
        glPushMatrix()
        glTranslatef(tx, ty, H / 2)
        glScalef(sx, sy, H)
        glutSolidCube(1)
        glPopMatrix()
        add_wall(offset_x + tx, offset_y + ty, sx, sy)

    if door_side == 'north':
        W(door_center - door_width / 2 - half_x / 2, room_h, half_x, T)
        W(door_center + door_width / 2 + half_x / 2, room_h, half_x, T)
    else:
        W(0, room_h, 2 * room_w, T)

    if door_side == 'south':
        W(door_center - door_width / 2 - half_x / 2, -room_h, half_x, T)
        W(door_center + door_width / 2 + half_x / 2, -room_h, half_x, T)
    else:
        W(0, -room_h, 2 * room_w, T)

    if door_side == 'east':
        W(room_w, door_center - door_width / 2 - half_y / 2, T, half_y)
        W(room_w, door_center + door_width / 2 + half_y / 2, T, half_y)
    else:
        W(room_w, 0, T, 2 * room_h)

    if door_side == 'west':
        W(-room_w, door_center - door_width / 2 - half_y / 2, T, half_y)
        W(-room_w, door_center + door_width / 2 + half_y / 2, T, half_y)
    else:
        W(-room_w, 0, T, 2 * room_h)

    glPopMatrix()

def boss_room(offset_x=0, offset_y=0, room_w=350, room_h=700, door_side='west', door_center=0, door_width=160.0):
    H = 250
    T = 5
    glPushMatrix()
    glTranslatef(offset_x, offset_y, 0)

    STEP = 40
    LIGHT = (0.6, 0.6, 0.6)
    DARK = (0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    for x in range(-room_w, room_w, STEP):
        for y in range(-room_h, room_h, STEP):
            shade = ((x // STEP + y // STEP) & 1)
            set_color(*(LIGHT if shade else DARK))
            glVertex3f(x, y, 0)
            glVertex3f(x + STEP, y, 0)
            glVertex3f(x + STEP, y + STEP, 0)
            glVertex3f(x, y + STEP, 0)
    glEnd()

    set_color(0.2, 0.1, 0.1)
    half_x = (2 * room_w - door_width) / 2
    half_y = (2 * room_h - door_width) / 2

    def W(tx, ty, sx, sy):
        glPushMatrix()
        glTranslatef(tx, ty, H / 2)
        glScalef(sx, sy, H)
        glutSolidCube(1)
        glPopMatrix()
        add_wall(offset_x + tx, offset_y + ty, sx, sy)

    if door_side == 'north':
        W(door_center - door_width / 2 - half_x / 2, room_h, half_x, T)
        W(door_center + door_width / 2 + half_x / 2, room_h, half_x, T)
    else:
        W(0, room_h, 2 * room_w, T)
    if door_side == 'south':
        W(door_center - door_width / 2 - half_x / 2, -room_h, half_x, T)
        W(door_center + door_width / 2 + half_x / 2, -room_h, half_x, T)
    else:
        W(0, -room_h, 2 * room_w, T)
    if door_side == 'east':
        W(room_w, door_center - door_width / 2 - half_y / 2, T, half_y)
        W(room_w, door_center + door_width / 2 + half_y / 2, T, half_y)
    else:
        W(room_w, 0, T, 2 * room_h)

    if door_side == 'west':
        W(-room_w, door_center - door_width / 2 - half_y / 2, T, half_y)
        W(-room_w, door_center + door_width / 2 + half_y / 2, T, half_y)
        door_x = -room_w
        door_y = door_center
        glPushMatrix()
        glTranslatef(door_x, door_y, H * 0.4)
        glScalef(T, door_width, H * 0.8) 
        if score < 5:
            set_color(0.05, 0.8, 0.15)
            glutSolidCube(1)
            add_wall(offset_x + door_x, offset_y + door_y, T, door_width)
        glPopMatrix()
    else:
        W(-room_w, 0, T, 2 * room_h)

    glPopMatrix()

def draw_legs():
    if boss_dark_mode:
        set_color(0.1*0.5,0.1*0.5,0.1*0.5)
    else:
        set_color(0.1,0.1,0.1)
    glPushMatrix()
    glTranslatef(-7, 0, -41)
    gluCylinder(quadric, 7, 7, 40, 10, 10)
    glTranslatef(15, 0, 0)
    gluCylinder(quadric, 7, 7, 40, 10, 10)
    glPopMatrix()

def draw_man_and_weapon():

    glPushMatrix()

    if game_over:
        glTranslatef(man_pos[0], man_pos[1], 12)
        glRotatef(-man_angle, 0, 0, 1)
        glRotatef(+90, 1, 0, 0)                       
    else:
        glTranslatef(man_pos[0], man_pos[1], man_pos[2] + 40)
        glRotatef(-man_angle, 0, 0, 1)

    # body
    if boss_dark_mode:
        set_color(0.8*0.5,0.2*0.5,0.2*0.5)
    else:       
        set_color(0.8,0.2,0.2)
    gluCylinder(quadric, 20, 20, 40, 10, 10)

    if current_weapon == 'gun':
        glPushMatrix()
        glTranslatef(0, 22, 28)     # forward from torso center, chest height
        glRotatef(-90, 1, 0, 0)   
        if boss_dark_mode:
            set_color(0.6*0.5,0.6*0.5,0.65*0.5)
        else:      
            set_color(0.6,0.6,0.65)
        gluCylinder(quadric, 8.0, 2.0, 42.0, 18, 6)
        glPopMatrix()

    # head
    glPushMatrix()
    glTranslatef(0, 0, 52)
    if boss_dark_mode: set_color(0.9*0.5,0.7*0.5,0.5*0.5)
    else:              set_color(0.9,0.7,0.5)
    gluSphere(quadric, 12, 10, 10)
    glPopMatrix()

    # left arm
    if boss_dark_mode: set_color(0.2*0.5,0.2*0.5,0.8*0.5)
    else:              set_color(0.2,0.2,0.8)
    glPushMatrix()
    glTranslatef(-23, 0, 0)
    gluCylinder(quadric, 5, 5, 40, 10, 10)
    glPopMatrix()

    # right arm + sword when sword selected
    glPushMatrix()
    glTranslatef(23, 0, 0)
    gluCylinder(quadric, 5, 5, 40, 10, 10)
    glTranslatef(0, 0, 40)

    if current_weapon == 'sword':
        swing_rot = 0.0
        if sword_swinging:
            t = min(1.0, (int((time.time() - start_time) * 1000) - sword_swing_start) / float(sword_swing_duration_ms))
            swing_rot = -sword_arc_deg * 0.5 + t * sword_arc_deg

        glPushMatrix()
        glRotatef(swing_rot, 0, 0, 1)
        glTranslatef(0, 16, -10)
        glRotatef(20, 0, 0, 1)

        if boss_dark_mode:
            set_color(0.25*0.5,0.2*0.5,0.2*0.5)
        else:
            set_color(0.25,0.2,0.2)
        glPushMatrix()
        glScalef(8, 3, 3)
        glutSolidCube(1)
        glPopMatrix()
        # blade
        if boss_dark_mode: set_color(0.90*0.5,0.90*0.5,1.0*0.5)
        else:              set_color(0.90,0.90,1.0)
        glTranslatef(0, 30, 0)
        glPushMatrix(); glScalef(sword_thickness, sword_length, 3.2); glutSolidCube(1); glPopMatrix()
        glPopMatrix()

    glPopMatrix()

    # LEGS
    draw_legs()

    glPopMatrix()

class Ghost:
    def __init__(self, x, y, z, angle):
        self.pos = [x, y, z]
        self.angle = angle
        self.body_height = 60
        self.body_radius_top = 20
        self.body_radius_bottom = 25
        self.head_radius = 20
        self.speed = 0.85
        self.scale = 1.0

    def move_towards_player(self, player_pos):
        vx = player_pos[0] - self.pos[0]
        vy = player_pos[1] - self.pos[1]
        d = math.hypot(vx, vy)
        if d > 0:
            vx /= d; vy /= d
            self.pos[0] += vx * self.speed
            self.pos[1] += vy * self.speed
            self.angle = (math.degrees(math.atan2(vy, vx)) + 90) % 360

    def draw(self):
        t = int((time.time() - start_time) * 1000) * 0.002
        self.scale = 1.0 + 0.2 * math.sin(t + (self.pos[0] + self.pos[1]) * 0.001)

        dx = man_pos[0] - self.pos[0]
        dy = man_pos[1] - self.pos[1]
        head_yaw = math.degrees(math.atan2(dy, dx))

        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glScalef(self.scale, self.scale, self.scale)

        # body
        set_color(0.15, 0.0, 0.20)
        glPushMatrix()
        glRotatef(-self.angle, 0, 0, 1)
        gluCylinder(quadric, self.body_radius_top, self.body_radius_bottom, self.body_height, 10, 10)
        glPopMatrix()

        # head
        glPushMatrix()
        glTranslatef(0, 0, self.body_height)
        set_color(0.97, 0.97, 0.99)
        gluSphere(quadric, self.head_radius, 16, 16)

        glRotatef(head_yaw, 0, 0, 1)
        set_color(0, 0, 0)
        for x_off in (-8, +8):
            glPushMatrix()
            glTranslatef(x_off, +12, 0)
            gluSphere(quadric, 4, 10, 10)
            glPopMatrix()
        glPopMatrix()

        glPopMatrix()

    def is_hit_by_laser(self, laser):
        ghost_head_z = self.pos[2] + self.body_height
        dist = math.sqrt((self.pos[0] - laser['x']) ** 2 +
                         (self.pos[1] - laser['y']) ** 2 +
                         (ghost_head_z - laser['z']) ** 2)
        return dist < (self.head_radius + 15)

class Treasure:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.size = 35
        self.rotation = 0
        self.float_offset = 0

    def update(self):
        t = int((time.time() - start_time) * 1000) * 0.001
        self.rotation = int(t * 120) % 360
        self.float_offset = 5 * math.sin(t + self.pos[0] * 0.1)

    def draw(self):
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2] + self.float_offset)
        glRotatef(self.rotation, 0, 0, 1)
        set_color(0.6, 0.4, 0.1)
        glPushMatrix(); glScalef(self.size, self.size * 0.7, self.size * 0.5); glutSolidCube(1); glPopMatrix()
        glPushMatrix(); glTranslatef(0, 0, self.size * 0.25); set_color(0.8, 0.6, 0.2); glScalef(self.size, self.size * 0.7, self.size * 0.25); glutSolidCube(1); glPopMatrix()
        glPushMatrix(); glTranslatef(0, 0, self.size * 0.5); set_color(1.0, 0.84, 0.0); gluSphere(quadric, self.size * 0.2, 10, 10); glPopMatrix()
        glPopMatrix()

def initialize_ghosts(n):
    global ghosts
    ghosts = []
    for _ in range(n):
        xmin, xmax, ymin, ymax = random.choice(spawn_zones)
        x = random.uniform(xmin, xmax)
        y = random.uniform(ymin, ymax)
        ghosts.append(Ghost(x, y, 0, random.uniform(0, 360)))

def initialize_treasures(n):
    global treasures
    treasures = []
    room_zones = spawn_zones[3:-2]
    MARGIN = 50
    for _ in range(n):
        xmin, xmax, ymin, ymax = random.choice(room_zones)
        x = random.uniform(xmin + MARGIN, xmax - MARGIN)
        y = random.uniform(ymin + MARGIN, ymax - MARGIN)
        dx, dy = x - man_pos[0], y - man_pos[1]
        if math.hypot(dx, dy) < 200:
            sgnx = 1 if dx >= 0 else -1
            sgny = 1 if dy >= 0 else -1
            x = max(min(x + sgnx * 200, xmax - MARGIN), xmin + MARGIN)
            y = max(min(y + sgny * 200, ymax - MARGIN), ymin + MARGIN)
        treasures.append(Treasure(x, y, 50))

def initialize_traps():
    global traps
    traps = []
    random.seed(7)
    for (cx, cy, amp, spd, axis) in [
        (-100, -450, 120, 0.024, 'x'),
        (800, -600, 90, 0.031, 'y'),
        (1400, -300, 140, 0.018, 'x'),
        (500, -950, 110, 0.026, 'y'),
    ]:
        traps.append({
            'x': float(cx), 'y': float(cy), 'z': 15.0,
            'size': 30.0, 'phase': random.uniform(0, math.pi * 2),
            'speed': spd, 'amplitude': amp, 'axis': axis
        })

def respawn_ghost(i):
    xmin, xmax, ymin, ymax = random.choice(spawn_zones)
    x = random.uniform(xmin, xmax)
    y = random.uniform(ymin, ymax)
    ghosts[i].pos = [x, y, 0]
def reset_game():
    global man_pos, man_angle, player_life, score, lasers, ghosts, treasures
    global current_weapon, gun_ammo, is_reloading, reload_end_time, sword_swinging
    global game_over, victory, boss_fight_active, teleport_cooldown_until, next_damage_ok_at
    global boss_dark_mode, highlight_mode, player_lying

    man_pos[:] = [0, 0, 0]
    man_angle = 0
    player_life = 10
    score = 0
    lasers.clear()
    current_weapon = 'gun'
    gun_ammo = magazine_size
    is_reloading = False
    reload_end_time = 0
    sword_swinging = False
    game_over = False
    victory = False
    player_lying = False
    boss_fight_active = False
    teleport_cooldown_until = 0
    next_damage_ok_at = 0
    boss_dark_mode = False
    highlight_mode = False

    boss.pos[:] = [2650, -400, 0]
    boss.health = 200
    boss.alive = True

    initialize_ghosts(12)
    initialize_treasures(5)
    initialize_traps()

def spawn_laser():
    global gun_ammo, last_shot_time, show_reload_hint_ticks
    now = int((time.time() - start_time) * 1000)
    if is_reloading:
        return
    if gun_ammo <= 0:
        show_reload_hint_ticks = 180
        return
    if now - last_shot_time < shot_cooldown_ms:
        return
    a = math.radians(man_angle)

    x = man_pos[0] + math.sin(a) * 28
    y = man_pos[1] + math.cos(a) * 28
    z = man_pos[2] + 55
    lasers.append({'x': x, 'y': y, 'z': z, 'angle': man_angle})
    last_shot_time = now
    gun_ammo -= 1

def _cone_hit(px, py, facing_deg, tx, ty, max_dist, arc_deg):
    dx = tx - px
    dy = ty - py
    d = math.hypot(dx, dy)
    if d > max_dist or d == 0:
        return False
    fx = math.sin(math.radians(facing_deg))
    fy = math.cos(math.radians(facing_deg))
    vx = dx / d
    vy = dy / d
    cos_thresh = math.cos(math.radians(arc_deg * 0.5))
    return (fx * vx + fy * vy) >= cos_thresh

def perform_sword_strike():
    hits = 0
    px, py = man_pos[0], man_pos[1]
    facing = man_angle

    for i, g in enumerate(ghosts):
        if _cone_hit(px, py, facing, g.pos[0], g.pos[1], sword_range, sword_arc_deg):
            respawn_ghost(i)
            hits += 1

    if boss.alive and _cone_hit(px, py, facing, boss.pos[0], boss.pos[1], sword_range + 20, sword_arc_deg):
        boss.take_damage(sword_boss_damage)
        hits += 1
    return hits

def draw_lasers():
    set_color(1, 0, 0)
    glLineWidth(6)
    glBegin(GL_LINES)
    for L in lasers:
        a = math.radians(L['angle'])
        glVertex3f(L['x'], L['y'], L['z'])
        glVertex3f(L['x'] + math.sin(a) * 40, L['y'] + math.cos(a) * 40, L['z'])
    glEnd()


def move_lasers():
    for L in lasers[:]:
        speed = 12
        a = math.radians(L['angle'])
        L['x'] += math.sin(a) * speed
        L['y'] += math.cos(a) * speed
        if abs(L['x']) > GRID_LENGTH or abs(L['y']) > GRID_LENGTH:
            lasers.remove(L); continue

        for i, g in enumerate(ghosts):
            if g.is_hit_by_laser(L):
                respawn_ghost(i)
                if L in lasers: lasers.remove(L)
                break

        if L in lasers and boss.alive:
            if math.hypot(L['x'] - boss.pos[0], L['y'] - boss.pos[1]) < 140:
                boss.take_damage(10)
                lasers.remove(L)

def update_traps_and_collide():
    global player_life, game_over, player_lying
    t = int((time.time() - start_time) * 1000) * 0.001
    for tr in traps:
        if tr['axis'] == 'x':
            tr['x'] += math.sin(t * (tr['speed'] * 60.0) + tr['phase']) * 0.7
        else:
            tr['y'] += math.cos(t * (tr['speed'] * 60.0) + tr['phase']) * 0.7
        if not cheat_mode and math.hypot(tr['x'] - man_pos[0], tr['y'] - man_pos[1]) < (tr['size'] * 0.7):
            if can_take_damage():
                player_life -= 1
                mark_damage_window()
                if player_life <= 0:
                    game_over = True
                    player_lying = True

def draw_traps():
    set_color(0.7, 0.0, 0.0)
    for tr in traps:
        glPushMatrix()
        glTranslatef(tr['x'], tr['y'], tr['z'])
        glRotatef(int((time.time() - start_time) * 1000) * 0.2 % 360, 0, 0, 1)
        glScalef(tr['size'], tr['size'], tr['size'])
        glutSolidCube(1)
        glPopMatrix()

def check_teleport():
    global teleport_cooldown_until
    now = int((time.time() - start_time) * 1000)
    if now < teleport_cooldown_until:
        return
    for i, (tx, ty, r) in enumerate(teleport_pads):
        if math.hypot(man_pos[0] - tx, man_pos[1] - ty) <= r:
            choices = [k for k in range(len(teleport_pads)) if k != i]
            j = random.choice(choices)
            nx, ny, _ = teleport_pads[j]
            man_pos[0], man_pos[1] = nx, ny
            teleport_cooldown_until = now + 1000  # 1s
            break

def draw_teleport_pads():
    for (tx, ty, r) in teleport_pads:
        set_color(0.6, 0.2, 0.8)  # purple
        glPushMatrix()
        glTranslatef(tx, ty, 1.0)
        segments = 48
        glBegin(GL_LINES)
        for i in range(segments):
            a1 = (i / float(segments)) * 2.0 * math.pi
            a2 = ((i + 1) / float(segments)) * 2.0 * math.pi
            glVertex3f(math.cos(a1) * r, math.sin(a1) * r, 0.0)
            glVertex3f(math.cos(a2) * r, math.sin(a2) * r, 0.0)
        glEnd()
        glPopMatrix()


def _draw_circle_xy(x, y, z, radius, segments=36):
    glPushMatrix()
    glTranslatef(x, y, z)
    glBegin(GL_LINES)
    for i in range(segments):
        a1 = (i / float(segments)) * 2.0 * math.pi
        a2 = ((i + 1) / float(segments)) * 2.0 * math.pi
        glVertex3f(math.cos(a1) * radius, math.sin(a1) * radius, 0.0)
        glVertex3f(math.cos(a2) * radius, math.sin(a2) * radius, 0.0)
    glEnd()
    glPopMatrix()


def _draw_square_xy(x, y, z, half):
    glPushMatrix()
    glTranslatef(x, y, z)
    glBegin(GL_LINES)
    # bottom edge
    glVertex3f(-half, -half, 0)
    glVertex3f( half, -half, 0)
    # right edge
    glVertex3f( half, -half, 0)
    glVertex3f( half,  half, 0)
    # top edge
    glVertex3f( half,  half, 0)
    glVertex3f(-half,  half, 0)
    # left edge
    glVertex3f(-half,  half, 0)
    glVertex3f(-half, -half, 0)
    glEnd()
    glPopMatrix()

def draw_highlights():
    glDisable(GL_DEPTH_TEST)
    set_color(0.2, 1.0, 0.4)
    glLineWidth(2.5)
    for g in ghosts:
        _draw_circle_xy(g.pos[0], g.pos[1], 2.0, g.body_radius_bottom + 20, 32)
    for t in treasures:
        _draw_square_xy(t.pos[0], t.pos[1], 2.0, t.size + 10)
    if boss.alive:
        _draw_circle_xy(boss.pos[0], boss.pos[1], 2.0, 140, 48)
    glEnable(GL_DEPTH_TEST)

def start_reload():
    global is_reloading, reload_end_time
    if is_reloading: return
    if gun_ammo == magazine_size: return
    is_reloading = True
    reload_end_time = int((time.time() - start_time) * 1000) + reload_duration_ms

def keyboardListener(key, x, y):
    global keys_pressed, jumping, jump_velocity, cheat_mode, current_weapon, highlight_mode
    keys_pressed.add(key)

    if key == b' ' and not jumping:
        jumping = True; jump_velocity = 10
    if key in (b'c', b'C'):
        cheat_mode = not cheat_mode
    if key in (b'r', b'R'):
        reset_game()
    if key in (b'x', b'X'):
        current_weapon = 'sword' if current_weapon == 'gun' else 'gun'
    if key in (b'l', b'L'):
        start_reload()
    if key in (b'v', b'V'):
        highlight_mode = not highlight_mode

def keyboardUpListener(key, x, y):
    keys_pressed.discard(key)

def specialKeyListener(key, x, y):
    global cam_back, cam_height, cam_yaw_offset
    if key == GLUT_KEY_LEFT:  cam_yaw_offset -= 4.0
    if key == GLUT_KEY_RIGHT: cam_yaw_offset += 4.0
    if key == GLUT_KEY_UP:    cam_height = min(420.0, cam_height + 8.0)
    if key == GLUT_KEY_DOWN:  cam_height = max(140.0, cam_height - 8.0)

def mouseListener(button, state, x, y):
    global first_person_mode, sword_swinging, sword_swing_start
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if current_weapon == 'gun':
            spawn_laser()
        else:
            if not sword_swinging:
                sword_swinging = True
                sword_swing_start = int((time.time() - start_time) * 1000)
                perform_sword_strike()
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        first_person_mode = not first_person_mode

def setupCamera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 4000)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    if first_person_mode:
        eye_x, eye_y, eye_z = man_pos[0], man_pos[1], man_pos[2] + 95
        a = math.radians(man_angle)
        eye_x += math.sin(a) * 15
        eye_y += math.cos(a) * 15
        center_x = eye_x + math.sin(a)
        center_y = eye_y + math.cos(a)
        center_z = eye_z
        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0, 0, 1)
    else:
        yaw = math.radians(man_angle + cam_yaw_offset)
        eye_x = man_pos[0] - math.sin(yaw) * cam_back
        eye_y = man_pos[1] - math.cos(yaw) * cam_back
        eye_z = man_pos[2] + cam_height
        gluLookAt(eye_x, eye_y, eye_z, man_pos[0], man_pos[1], man_pos[2] + 80.0, 0, 0, 1)


def idle():
    global man_pos, jumping, jump_velocity, man_angle
    global is_reloading, gun_ammo, sword_swinging, show_reload_hint_ticks
    global boss_fight_active, player_life, game_over, boss_dark_mode, player_lying

    if game_over or victory:
        glutPostRedisplay(); return

    step = man_speed
    a = math.radians(man_angle)
    dx = dy = 0
    if b'w' in keys_pressed: dx += math.sin(a) * step; dy += math.cos(a) * step
    if b's' in keys_pressed: dx -= math.sin(a) * step; dy -= math.cos(a) * step
    if b'a' in keys_pressed: man_angle -= 2
    if b'd' in keys_pressed: man_angle += 2

    # Move with wall collision (unless cheat)
    if not cheat_mode:
        nx, ny = resolve_move_with_walls(man_pos[0], man_pos[1], man_pos[0] + dx, man_pos[1] + dy)
        man_pos[0], man_pos[1] = nx, ny
    else:
        man_pos[0] += dx; man_pos[1] += dy

    # Jumping
    if jumping:
        man_pos[2] += jump_velocity
        jump_velocity -= 1
        if man_pos[2] <= 0:
            man_pos[2] = 0; jumping = False; jump_velocity = 0

    # Reload timing
    if is_reloading and int((time.time() - start_time) * 1000) >= reload_end_time:
        is_reloading = False
        gun_ammo = magazine_size

    # Sword swing timing
    if sword_swinging and (int((time.time() - start_time) * 1000) - sword_swing_start) >= sword_swing_duration_ms:
        sword_swinging = False

    # Bullets / traps
    move_lasers()
    update_traps_and_collide()

    for i, g in enumerate(ghosts):
        g.move_towards_player(man_pos)
        if not cheat_mode and math.hypot(man_pos[0] - g.pos[0], man_pos[1] - g.pos[1]) < (25 + g.body_radius_bottom):
            if can_take_damage():
                player_life -= 1
                mark_damage_window()
                respawn_ghost(i)
                if player_life <= 0:
                    game_over = True
                    player_lying = True

    for t in treasures:
        t.update()
    check_treasure_collision()

    check_teleport()

    gate_x, gate_y = 2200, -400
    if score >= 5 and not boss_fight_active:
        if abs(man_pos[0] - gate_x) < 60 and abs(man_pos[1] - gate_y) < 60:
            boss_fight_active = True
            boss_dark_mode = True

    boss.update(man_pos)

    if boss_fight_active and boss.alive and not cheat_mode:
        if math.hypot(man_pos[0] - boss.pos[0], man_pos[1] - boss.pos[1]) < 125:
            if can_take_damage():
                player_life -= 1
                mark_damage_window()
                if player_life <= 0:
                    game_over = True
                    player_lying = True

    if show_reload_hint_ticks > 0:
        show_reload_hint_ticks -= 1

    glutPostRedisplay()

def check_treasure_collision():
    global score
    player_radius = 25
    for tr in treasures[:]:
        if math.hypot(man_pos[0] - tr.pos[0], man_pos[1] - tr.pos[1]) < (player_radius + tr.size):
            treasures.remove(tr)
            score += 1

def draw_scene_geometry():
    room1()  # center: (0,0), extents x[-300,300], y[-300,300]

    draw_hallway()  # EW: x[-300,2200], y[-600,-300]; NS: x[1900,2200], y[-300,300]

    room2(offset_x=0,    offset_y=-900, door_side='north', door_center=0,  door_width=140.0)  # x[-300,300],  y[-1200,-600]
    room2(offset_x=600,  offset_y=0,    door_side='south', door_center=0,  door_width=140.0)  # x[300,900],   y[-300,300]

    room3(offset_x=500,  offset_y=-900, room_w=300, room_h=300, door_side='north', door_center=50,  door_width=140.0)  # x[200,800],   y[-1200,-600]
    room3(offset_x=1400, offset_y=0,    room_w=500, room_h=300, door_side='south', door_center=50,  door_width=160.0)  # x[900,1900],  y[-300,300]
    room3(offset_x=1300, offset_y=-900, room_w=500, room_h=300, door_side='north', door_center=50,  door_width=160.0)  # x[800,1800],  y[-1200,-600]
    room3(offset_x=2000, offset_y=-900, room_w=200, room_h=300, door_side='north', door_center=50,  door_width=140.0)  # x[1800,2200], y[-1200,-600]

    boss_room(offset_x=2550, offset_y=-400, room_w=350, room_h=700, door_side='west', door_center=0, door_width=160.0)  # west wall at x = 2200

def draw_low_hp_text():
    if player_life >= 3 or game_over:
        return
    set_color(1.0, 0.0, 0.0)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(470, 400)
    for ch in "HP LOW!":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def showScreen():
    collision_walls.clear()
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setupCamera()
    draw_scene_geometry()

    if score < 5:
        add_wall(2200, -400, 100, 100)

    draw_traps()
    draw_teleport_pads()
    draw_man_and_weapon()

    for g in ghosts:
        g.draw()
    for t in treasures:
        t.draw()
    draw_lasers()
    boss.draw()

    if highlight_mode:
        draw_highlights()

    draw_text(10, 770, "Haunted House")
    weap = f"Weapon: {current_weapon.upper()}"
    draw_text(10, 748, f"Treasures Collected {score}/5  |  HP: {player_life}  |  {weap}")
    if current_weapon == 'gun':
        status = "(Reloading…)" if is_reloading else ""
        draw_text(10, 726, f"Ammo: {gun_ammo}/{magazine_size} {status}")
        draw_text(10, 704, "L-Reload  X-Switch  C-Cheat Mode  V-Highlight R-Reset")
        if (gun_ammo == 0) and (not is_reloading) and (show_reload_hint_ticks > 0):
            draw_text(360, 726, "Press L to reload!", GLUT_BITMAP_HELVETICA_18)
    else:
        draw_text(10, 726, "L-Reload (gun)  X-Switch  C-Cheat Mode  V-Highlight R-Reset")
        draw_text(10, 704, "Left click: Sword swing")

    if boss_fight_active:
        draw_text(10, 682, f"Boss Health: {boss.health}")
    if victory:
        draw_text(430, 420, "YOU WIN!")
    if game_over:
        draw_text(430, 420, "GAME OVER")

    draw_low_hp_text()
    glutSwapBuffers()

def main():
    global quadric
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(50, 50)
    glutCreateWindow(b"3D Haunted House")

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glEnable(GL_DEPTH_TEST)
    glClearColor(0.02, 0.02, 0.03, 1.0)

    quadric = gluNewQuadric()

    reset_game()
    glutMainLoop()

if __name__ == "__main__":
    main()
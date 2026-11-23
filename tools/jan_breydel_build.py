#!/usr/bin/env python3
"""Build a lightweight, game-ready Jan Breydelstadion GLB without Blender.

Geometry is based on the current ground's distinctive four-stand bowl,
partially open corners, green cantilever roofs and floodlight pylons. Dimensions
are aligned to the 105 x 68 m pitch. Run: python3 tools/jan_breydel_build.py
"""
import json, math, os, struct

OUT = os.path.join(os.path.dirname(__file__), "../media/models/stadiums/jan_breydel.glb")
MATS = [
    ("concrete", (0.34, 0.37, 0.36, 1)),
    ("weathered_concrete", (0.24, 0.27, 0.26, 1)),
    ("roof_green", (0.075, 0.19, 0.105, 1)),
    ("roof_edge", (0.12, 0.24, 0.15, 1)),
    ("blue_seats", (0.015, 0.07, 0.30, 1)),
    ("light_seats", (0.72, 0.76, 0.73, 1)),
    ("yellow_seats", (0.92, 0.68, 0.06, 1)),
    ("steel", (0.22, 0.25, 0.24, 1)),
    ("glass", (0.16, 0.24, 0.25, 1)),
    ("pitch", (0.045, 0.24, 0.065, 1)),
    ("line", (0.82, 0.85, 0.78, 1)),
    ("dark", (0.045, 0.055, 0.05, 1)),
]
TRIS = [[] for _ in MATS]

def tri(a, b, c, mat):
    TRIS[mat].extend((*a, *b, *c))

def quad(a, b, c, d, mat):
    tri(a, b, c, mat); tri(a, c, d, mat)

def box(x0,y0,z0,x1,y1,z1,mat):
    a=(x0,y0,z0); b=(x1,y0,z0); c=(x1,y1,z0); d=(x0,y1,z0)
    e=(x0,y0,z1); f=(x1,y0,z1); g=(x1,y1,z1); h=(x0,y1,z1)
    for pts in ((a,d,c,b),(e,f,g,h),(a,b,f,e),(b,c,g,f),(c,d,h,g),(d,a,e,h)):
        quad(*pts,mat)

def beam(p,q,r,mat):
    # Robust rectangular structural member between two 3D points.
    dx,dy,dz=(q[i]-p[i] for i in range(3)); L=math.sqrt(dx*dx+dy*dy+dz*dz)
    if L < 1e-5: return
    ux,uy,uz=dx/L,dy/L,dz/L
    ax,ay=(-uy,ux) if abs(uz)>.8 else (-uy,ux)
    al=math.hypot(ax,ay) or 1; ax,ay=ax/al*r,ay/al*r
    bx,by,bz=uy*uz*r,-ux*uz*r,(ux*ux+uy*uy)*r
    pts=[]
    for t in (0,1):
        x,y,z=(p[0]+dx*t,p[1]+dy*t,p[2]+dz*t)
        pts += [(x+sx*ax+tx*bx,y+sx*ay+tx*by,z+tx*bz) for sx,tx in ((-1,-1),(1,-1),(1,1),(-1,1))]
    for i in range(4):
        j=(i+1)%4; quad(pts[i],pts[j],pts[j+4],pts[i+4],mat)
    quad(*pts[4:],mat); quad(*pts[:4],mat)

def roof_panel(corners, mat):
    quad(*corners,mat); quad(corners[3],corners[2],corners[1],corners[0],mat)

# Pitch and perimeter apron. Pitch uses local y as its long axis, matching the
# game's catalog convention; the 105 m direction runs along world X.
box(-52.5,-34,0,52.5,34,0.22,9)
box(-0.07,-34.2,0.27,0.07,34.2,0.29,10)
for x in (-52.5,52.5): box(x-0.07,-34.2,.27,x+0.07,34.2,.29,10)
for y in (-34,34): box(-52.5,y-.07,.27,52.5,y+.07,.29,10)
for x in (-36.5,36.5):
    for y in (-20.16,20.16): box(x-.07,y-.07,.27,x+.07,y+.07,.29,10)
for x in (-41.5,41.5):
    for y in (-9.16,9.16): box(x-.07,y-.07,.27,x+.07,y+.07,.29,10)
for sign in (-1,1):
    endx=sign*52.5; innerx=sign*36.0
    for xx in (endx,innerx): box(xx-.07,-20.16,.27,xx+.07,20.16,.29,10)
    for yy in (-20.16,20.16):
        box(min(endx,innerx),yy-.07,.27,max(endx,innerx),yy+.07,.29,10)
    box(sign*47.0-.07,-9.16,.27,sign*47.0+.07,9.16,.29,10)
    for yy in (-9.16,9.16): box(min(sign*52.5,sign*47.0),yy-.07,.27,max(sign*52.5,sign*47.0),yy+.07,.29,10)
for i in range(96):
    a=2*math.pi*i/96; b=2*math.pi*(i+1)/96
    quad((9.05*math.cos(a),9.05*math.sin(a),.29),(9.05*math.cos(b),9.05*math.sin(b),.29),
         (9.25*math.cos(b),9.25*math.sin(b),.29),(9.25*math.cos(a),9.25*math.sin(a),.29),10)

# Four independent covered stands. Each has exposed, repeated concrete
# terraces, blue seating with white/yellow seat patterns and a steep rear wall.
# The north-west and south-west corners are intentionally left open as on site.
NROWS, NCOLS = 22, 102
GLYPHS = {
 'A':('0110','1001','1001','1111','1001','1001','1001'), 'B':('1110','1001','1001','1110','1001','1001','1110'),
 'D':('1110','1001','1001','1001','1001','1001','1110'), 'E':('1111','1000','1000','1110','1000','1000','1111'),
 'I':('111','010','010','010','010','010','111'), 'J':('0011','0001','0001','0001','1001','1001','0110'),
 'L':('1000','1000','1000','1000','1000','1000','1111'), 'N':('1001','1101','1101','1011','1011','1001','1001'),
 'O':('0110','1001','1001','1001','1001','1001','0110'), 'R':('1110','1001','1001','1110','1010','1001','1001'),
 'S':('0111','1000','1000','0110','0001','0001','1110'), 'T':('1111','0110','0110','0110','0110','0110','0110'),
 'Y':('1001','1001','0101','0010','0010','0010','0010')
}
def seats_on_stand(side, row, z, a0, a1, count, end=False, upper=False):
    for col in range(count):
        u=(col+.5)/count; p=a0+(a1-a0)*u; w=(a1-a0)/count*.78; color=4
        if col%17 in (0,1): color=6
        if row%9==0 and col%13==0: color=5
        if side>0 and not end and 7<=row<14 and col<90:
            ch=col//5; px=col%5; word='JAN BREYDEL STADION'
            if ch<len(word) and px<4 and word[ch]!=' ' and px<len(GLYPHS[word[ch]][13-row]) and GLYPHS[word[ch]][13-row][px]=='1': color=5
        if not end:
            y=side*(38.0+row*.72)
            box(p-w/2,min(y,y+side*.28),z,p+w/2,max(y,y+side*.28),z+.10,color)
            box(p-w/2,min(y+side*.20,y+side*.34),z+.10,p+w/2,max(y+side*.20,y+side*.34),z+.44,color)
        else:
            x=side*((70.0 if upper else 60.4)+row*.74)
            box(min(x,x+side*.28),p-w/2,z,max(x,x+side*.28),p+w/2,z+.10,color)
            box(min(x+side*.20,x+side*.34),p-w/2,z+.10,max(x+side*.20,x+side*.34),p+w/2,z+.44,color)

def stand(side, end=False):
    # The long east/west stands are one tier. North/south received an upper tier in 1999.
    tiers=[(28,1.0,False)] if not end else [(16,1.0,False),(15,9.9,True)]
    for rows,zbase,upper in tiers:
        for row in range(rows):
            z=zbase+row*(.50 if upper else .48)
            if not end:
                lo,hi=-59.5,59.5; inner=side*(37.8+row*.72); outer=side*(38.22+row*.72)
                box(lo,min(inner,outer),z-.22,hi,max(inner,outer),z-.03,0 if row%5 else 1)
                seats_on_stand(side,row,z,lo,hi,154)
            else:
                lo,hi=-43.0,43.0; start=69.4 if upper else 59.8
                inner=side*(start+row*.74); outer=side*(start+.42+row*.74)
                box(min(inner,outer),lo,z-.22,max(inner,outer),hi,z-.03,0 if row%5 else 1)
                seats_on_stand(side,row,z,lo,hi,112,True,upper)
    if not end:
        y=side*59
        box(-62,min(0,y),13,62,max(0,y),16,1)
        box(-61,min(0,y),16,61,max(0,y),18,8)
    else:
        x=side*85
        box(min(0,x),-44,18,max(0,x),44,21,1)

stand(-1); stand(1); stand(-1,True); stand(1,True)

# Green cantilever roofs with the characteristic four separate roof wings.
# Slim steel trusses and fascia make the silhouette readable from the game camera.
for side in (-1,1):
    y0=side*40; y1=side*68
    roof_panel([(-64,y0,21.0),(64,y0,21.0),(64,y1,28.8),(-64,y1,28.8)],2)
    beam((-64,y1,28.8),(64,y1,28.8),1.0,3)
    for x in range(-60,61,3):
        beam((x,y0,20.4),(x,y1,28.4),.42,7)
        beam((x,y1,28.4),(min(x+3,64),y1,28.4),.22,7)
for side in (-1,1):
    x0=side*63; x1=side*88
    roof_panel([(x0,-47,21),(x0,47,21),(x1,47,27.8),(x1,-47,27.8)],2)
    beam((x1,-47,27.8),(x1,47,27.8),1,3)
    for y in range(-40,41,3): beam((x0,y,20.5),(x1,y,27.4),.4,7)

# Exposed concrete support piers, external stairs and concourse portals.
for side in (-1,1):
    for x in range(-54,55,18):
        beam((x,side*57,1),(x,side*64,20),1.15,0)
        beam((x-2,side*64,2),(x+2,side*64,2),.35,7)
        # exposed diagonal concrete braces below the cantilever
        beam((x-5,side*56,1),(x+5,side*58,12),.8,1)
        beam((x+5,side*56,1),(x-5,side*58,12),.8,0)
    for x in (-48,-24,0,24,48):
        box(x-1.6,side*57,7,x+1.6,side*61,14,8)
        box(x-2.5,side*58,14,x+2.5,side*60,14.5,6)
    # open galleries, safety rails and long rows of concourse glazing
    for z in (6.5,13.5):
        beam((-60,side*61,z),(60,side*61,z),.16,7)
        beam((-60,side*61,z+1),(60,side*61,z+1),.09,6)
        for x in range(-60,61,3): beam((x,side*61,z),(x,side*61,z+1),.045,7)
    for x in range(-57,58,6):
        box(x-2.1,side*59.2,4,x+2.1,side*59.45,6.5,8)
        box(x-2.1,side*59.2,7,x+2.1,side*59.45,9.5,8)
    # external zigzag access stairs with yellow handrails
    for x in (-42,-14,14,42):
        for flight in range(4):
            y0=side*(61+flight*1.4); y1=side*(62.4+flight*1.4)
            z0=1+flight*3.1; z1=z0+3.1
            beam((x-3,y0,z0),(x+3,y1,z1),.23,7)
            beam((x-3,y0,z0+1),(x+3,y1,z1+1),.07,6)
for side in (-1,1):
    for y in (-35,-17,0,17,35):
        beam((side*78,y,1),(side*84,y,19),1.0,0)
        box(side*78-1,min(y-1, y+1),7,side*84+1,max(y-1,y+1),14,8)
    # north and south facades have visible upper concourse entrances
    for y in range(-36,37,9):
        box(side*82.8,y-2.1,17,side*83.2,y+2.1,19.8,8)
        beam((side*83,y-2.4,16.8),(side*83,y+2.4,16.8),.12,6)

# Four tall, tapered floodlight towers: a signature element visible above the roof.
for x in (-64,64):
    for y in (-68,68):
        base=(x,y,25); top=(x,y,47)
        beam(base,top,1.05,7)
        for dx in (-2.6,-1.7,-.85,0,.85,1.7,2.6):
            box(x+dx-.28,y-1.1,46.5,x+dx+.28,y+1.1,47.3,10)
        beam((x-3,y,25),(x+3,y,46),.12,7)
        beam((x+3,y,25),(x-3,y,46),.12,7)

# Goals, corner flags and a roofed exterior ring at ground level.
for x in (-53.5,53.5):
    for y in (-3.66,3.66): beam((x,y,.3),(x,y,2.74),.12,5)
    beam((x,-3.66,2.74),(x,3.66,2.74),.12,5)
for x in (-78,78):
    for y in (-60,60): box(x-1,y-1,0,x+1,y+1,2.4,0)

# Exterior footprint, low dark service base, access ramps and perimeter supports.
box(-81,-62,-1,81,62,0.2,11)
for side in (-1,1):
    for x in range(-60,61,12):
        box(x-2,side*60,0,x+2,side*62,5,0)
        beam((x-2,side*62,1),(x+2,side*66,8),.28,7)

# Serialize triangle groups into a standards-compliant binary glTF 2.0.
bin_data=bytearray(); views=[]; accessors=[]; primitives=[]
def align4():
    while len(bin_data)%4: bin_data.append(0)
for mi,flat in enumerate(TRIS):
    if not flat: continue
    # Flat face normals are expanded per triangle; custom stadium is modest in size.
    positions=[]; normals=[]; inds=[]
    for i in range(0,len(flat),9):
        # Convert builder coordinates (x, lateral, up) to glTF/Three.js Y-up.
        a=(flat[i],flat[i+2],-flat[i+1]); b=(flat[i+3],flat[i+5],-flat[i+4]); c=(flat[i+6],flat[i+8],-flat[i+7])
        ux,uy,uz=b[0]-a[0],b[1]-a[1],b[2]-a[2]
        vx,vy,vz=c[0]-a[0],c[1]-a[1],c[2]-a[2]
        nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        l=math.sqrt(nx*nx+ny*ny+nz*nz) or 1; n=(nx/l,ny/l,nz/l)
        positions.extend((*a,*b,*c)); normals.extend((*n,*n,*n))
    align4(); po=len(bin_data); bin_data.extend(struct.pack('<%sf'%len(positions),*positions)); pl=len(bin_data)-po
    views.append({"buffer":0,"byteOffset":po,"byteLength":pl,"target":34962}); pv=len(views)-1
    xs=positions[0::3]; ys=positions[1::3]; zs=positions[2::3]
    accessors.append({"bufferView":pv,"componentType":5126,"count":len(positions)//3,"type":"VEC3","min":[min(xs),min(ys),min(zs)],"max":[max(xs),max(ys),max(zs)]}); pa=len(accessors)-1
    align4(); no=len(bin_data); bin_data.extend(struct.pack('<%sf'%len(normals),*normals)); nl=len(bin_data)-no
    views.append({"buffer":0,"byteOffset":no,"byteLength":nl,"target":34962}); nv=len(views)-1
    accessors.append({"bufferView":nv,"componentType":5126,"count":len(normals)//3,"type":"VEC3"}); na=len(accessors)-1
    primitives.append({"attributes":{"POSITION":pa,"NORMAL":na},"mode":4,"material":mi})

gltf={"asset":{"version":"2.0","generator":"Jan Breydel procedural stadium builder"},
      "scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"name":"Jan Breydelstadion","mesh":0}],
      "meshes":[{"name":"Jan Breydelstadion","primitives":primitives}],
      "materials":[{"name":n,"pbrMetallicRoughness":{"baseColorFactor":c,"metallicFactor":0.03,"roughnessFactor":0.86}} for n,c in MATS],
      "buffers":[{"byteLength":len(bin_data)}],"bufferViews":views,"accessors":accessors}
js=json.dumps(gltf,separators=(',',':')).encode('utf8')
while len(js)%4: js+=b' '
while len(bin_data)%4: bin_data.append(0)
total=12+8+len(js)+8+len(bin_data)
os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,'wb') as f:
    f.write(struct.pack('<4sII',b'glTF',2,total)); f.write(struct.pack('<I4s',len(js),b'JSON')); f.write(js)
    f.write(struct.pack('<I4s',len(bin_data),b'BIN\0')); f.write(bin_data)
print(f"Wrote {OUT} ({os.path.getsize(OUT):,} bytes; {sum(len(t)//9 for t in TRIS):,} triangles)")

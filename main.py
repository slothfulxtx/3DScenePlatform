import flask
from flask_cors import CORS
import orm
import json
import pdb
import os
import numpy as np
import base64
import time
import datetime
from io import BytesIO
from PIL import Image
from rec_release import fa_reshuffle
from autolayoutv2 import sceneSynthesis
from flask import Flask, render_template, send_file, request
# from generate_descriptor import sketch_search
# import blueprints for app to register; 
from main_audio import app_audio
from main_ls import app_ls
from main_magic import app_magic
from projection2d import objListCat, getobjCat
import random
import difflib

app = Flask(__name__)
app.register_blueprint(app_audio)
app.register_blueprint(app_ls)
app.register_blueprint(app_magic)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CORS(app)

with open('./latentspace/obj-semantic.json') as f:
    obj_semantic = json.load(f)

@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/")
def main():
    now = datetime.datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H-%M-%S")
    print(request.remote_addr, dt_string)
    return flask.send_from_directory("static", "index.html")

@app.route("/static/<fname>")
def send(fname):
    return flask.send_from_directory("static", fname)

@app.route("/objmeta/<obj>")
def objmeta(obj):
    m = orm.query_model_by_name(obj)
    if m is None:
        return json.dumps({})
    ret = {"id": m.id, "name": m.name, "semantic": m.category.wordnetSynset, "thumbnail": "/thumbnail/%d/" % (m.id,)}
    if (m.format == "OBJ"):
        ret["mesh"] = "/mesh/%s" % m.id
        ret["mtl"] = "/mtl/%s" % m.id
        ret["texture"] = "/texture/"
        return json.dumps(ret)

@app.route("/objmeta_by_id/<id>")
def objmeta_by_id(id):
    m = orm.query_model_by_id(id)
    ret = {"id": m.id, "name": m.name, "semantic": m.category.wordnetSynset, "thumbnail": "/thumbnail/%d/" % (m.id,)}
    if (m.format == "OBJ"):
        ret["mesh"] = "/mesh/%s" % m.id
        ret["mtl"] = "/mtl/%s" % m.id
        ret["texture"] = "/texture/"
        return json.dumps(ret)

@app.route("/mesh/<name>")
def mesh(name):
    # m = orm.query_model_by_id(id)
    # return flask.send_file(json.loads(m.resources)["mesh"])
    return flask.send_file(f'./dataset/object/{name}/{name}.obj')

@app.route("/thumbnail/<id>/<int:view>")
def thumbnail(id, view):
    m = orm.query_model_by_id(id)
    return flask.send_from_directory(os.path.join(".", "dataset", "objd20", m.name, "render20"),
                                     "render-%s-%d.png" % (m.name, view))

@app.route("/thumbnail/<name>")
def thumbnail_sk(name):
    # m = orm.query_model_by_id(id)
    # return flask.send_from_directory(os.path.join(".", "dataset", "object", m.name, "render20"), "render-%s-%d.png" % (m.name, 10))
    return flask.send_from_directory(os.path.join(".", "dataset", "object", name, "render20"), "render-%s-%d.png" % (name, 10))

@app.route("/mtl/<name>")
def mtl(name):
    # m = orm.query_model_by_id(id)
    # return flask.send_file(json.loads(m.resources)["mtl"])
    return flask.send_file(f'./dataset/object/{name}/{name}.mtl')

@app.route("/texture//<id>")
def texture(id):
    return flask.send_from_directory(os.path.join(".", "dataset", "texture"), id)

@app.route("/texture/<id>")
def texture_(id):
    return flask.send_from_directory(os.path.join(".", "dataset", "texture"), id)

@app.route("/query")
def textquery():
    kw=flask.request.args.get('kw', default = "", type = str) # keyword
    lo=flask.request.args.get('lo', default = 0, type = int) #
    hi=flask.request.args.get('hi', default = 100, type = int)
    models=orm.query_models(kw,(lo,hi))
    modelofid = orm.query_model_by_name(kw)
    if modelofid is not None:
        models.append(modelofid)
    ret=[{"id":m.id,"name":m.name,"semantic":m.category.wordnetSynset,"thumbnail":f"/thumbnail/{m.name}"} for m in models]
    if os.path.exists(f'./dataset/object/{kw}/{kw}.obj'):
        ret.append({
            "id": -1,
            "name": kw,
            "semantic": 'currentlyUnknown',
            "thumbnail":f"/thumbnail/{kw}"})
    return json.dumps(ret)

with open('./dataset/ChineseMapping.json', encoding='utf-8') as f:
    ChineseMapping = json.load(f)
@app.route("/query2nd")
def query2nd():
    kw=flask.request.args.get('kw', default = "", type = str) # keyword
    catMatches = difflib.get_close_matches(kw, list(ChineseMapping.keys()), 1)
    if len(catMatches) == 0:
        return json.dumps([])
    cat = ChineseMapping[catMatches[0]]
    print(f'get query: {cat}. ')
    random.shuffle(objListCat[cat])
    if len(objListCat[cat]) >= 20:
        modelIds = objListCat[cat][0:20]
    else:
        modelIds = objListCat[cat]
    ret=[{"name":modelId, "semantic":cat, "thumbnail":f"/thumbnail/{modelId}"} for modelId in modelIds]
    if os.path.exists(f'./dataset/object/{kw}/{kw}.obj'):
        ret.append({"name": kw, "semantic": getobjCat(kw), "thumbnail":f"/thumbnail/{kw}"})
    return json.dumps(ret)

@app.route("/room/<houseid>/<roomid>")
def roominfo(houseid, roomid):
    structs = {"c": "c.obj", "w": "w.obj", "f": "f.obj"}
    ret = [k for k in structs if os.path.isfile(os.path.join("dataset", "room", houseid, roomid + structs[k]))]
    return json.dumps(ret)

@app.route("/room/<houseid>/<roomid>f.obj")
def floor(houseid, roomid):
    return flask.send_file(os.path.join("dataset", "room", houseid, roomid + "f.obj"))

@app.route("/room/<houseid>/<roomid>w.obj")
def wall(houseid, roomid):
    return flask.send_file(os.path.join("dataset", "room", houseid, roomid + "w.obj"))

@app.route("/room/<houseid>/<roomid>c.obj")
def ceil(houseid, roomid):
    return flask.send_file(os.path.join("dataset", "room", houseid, roomid + "c.obj"))

@app.route("/room/<houseid>/<roomid>f.mtl")
def floor_mtl(houseid, roomid):
    return flask.send_file(os.path.join("dataset", "room", houseid, roomid + "f.mtl"))

@app.route("/room/<houseid>/<roomid>w.mtl")
def wall_mtl(houseid, roomid):
    return flask.send_file(os.path.join("dataset", "room", houseid, roomid + "w.mtl"))

@app.route("/room/<houseid>/<roomid>c.mtl")
def ceil_mtl(houseid, roomid):
    return flask.send_file(os.path.join("dataset", "room", houseid, roomid + "c.mtl"))

@app.route("/set_scene_configuration", methods=['POST', 'GET'])
def set_scene_configuration():
    if request.method == 'POST':
        with open('./temp.json', 'w') as f:
            json.dump(request.json, f)
        return "POST scene configuration. "
    if request.method == 'GET':
        return "Do not support using GET to configurate scene. "

@app.route("/sketch", methods=['POST', 'GET'])
def sketch():
    if request.method == 'POST':
        image_data = bytes(request.form.get('imgBase64'), encoding="ascii")
        imgdata = base64.b64decode(image_data)
        filename = './qs.png'
        with open(filename, 'wb') as f:
            f.write(imgdata)
        start_time = time.time()
        results = sketch_search('./qs.png', 400)
        end_time = time.time()
        tmp = []
        for i in results:
            if i not in tmp:
                tmp.append(i)
                if len(tmp) >= 20:
                    break
        results = tmp
        results = orm.query_model_by_names(results)
        ret = [
            {"id": m.id, "name": m.name, "semantic": m.category.wordnetSynset, "thumbnail": "/thumbnail/%d" % (m.id,)}
            for m in results if m != None]
        print("\r\n\r\n------- %s secondes --- \r\n\r\n" % (end_time - start_time))
        return json.dumps(ret)
    return "Post image! "

@app.route("/sklayout", methods=['POST', 'GET'])
def sklayout():
    if request.method == 'POST':
        return json.dumps(sceneSynthesis(request.json))
    if request.method == 'GET':
        return "Do not support using GET to using recommendation. "


@app.route("/reshuffle", methods=['POST', 'GET'])
def reshuffle():
    if request.method == 'POST':
        return json.dumps(fa_reshuffle(request.json))
    if request.method == 'GET':
        return "Do not support using GET to using recommendation. "

@app.route("/semantic/<obj_id>")
def semantic(obj_id):
    return obj_semantic[obj_id]

# https://icon-icons.com/icon/audience-theater-scene-curtains/54210
@app.route('/favicon.ico') 
def favicon(): 
    return flask.send_from_directory('static', 'iconfinder-stagingsite-4263528_117848.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=11425, threads=6)
    # app.run(host="0.0.0.0", port=11425, debug=True, threaded=True)

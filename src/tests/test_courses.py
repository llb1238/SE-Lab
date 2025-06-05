import pytest
import json

@pytest.fixture(autouse=True)
def login_admin(client):
    """保证在查询课程前已登录（admin/123456）"""
    resp = client.post(
        "/login",
        data=json.dumps({"username": "admin", "password": "123456", "role": "admin"}),
        content_type="application/json"
    )
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["success"] is True

@pytest.mark.usefixtures("reset_database")
class TestCourseAPI:

    def test_get_courses(self, client):
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        # 测试数据中至少有“软件工程”这门课
        names = [c["name"] for c in data["data"]]
        assert "软件工程" in names

    def test_add_course(self, client):
        new_course = {
            "name": "测试课程",
            "learn_time": "大一",
            "credit": 2,
            "usual_score": 20,
            "midterm_score": 30,
            "final_score": 50,
            "times": "星期五 10:30-12:10"
        }
        resp = client.post("/api/courses", data=json.dumps(new_course),
                           content_type="application/json")
        assert resp.status_code == 200
        j = resp.get_json()
        assert j["success"] is True
        cid = j["data"]["id"]

        # 再次获取确认新增
        allc = client.get("/api/courses").get_json()["data"]
        assert any(c["id"] == cid and c["name"] == "测试课程" for c in allc)

    def test_update_course(self, client):
        # 先添加
        add = {
            "name": "待修改课程",
            "learn_time": "大二",
            "credit": 3,
            "usual_score": 10,
            "midterm_score": 40,
            "final_score": 50,
            "times": "星期三 14:00-15:40"
        }
        cid = client.post("/api/courses", data=json.dumps(add),
                          content_type="application/json").get_json()["data"]["id"]

        # 更新
        upd = {
            "name": "已修改课程",
            "learn_time": "大三",
            "credit": 4,
            "usual_score": 25,
            "midterm_score": 25,
            "final_score": 50,
            "times": "星期一 8:30-10:10"
        }
        resp = client.put(f"/api/courses/{cid}", data=json.dumps(upd),
                          content_type="application/json")
        assert resp.status_code == 200
        j2 = resp.get_json()
        assert j2["success"] is True
        assert j2["data"]["name"] == "已修改课程"

    def test_delete_course(self, client):
        # 添加一门待删课程
        to_del = {
            "name": "待删除课程",
            "learn_time": "大四",
            "credit": 1,
            "usual_score": 30,
            "midterm_score": 30,
            "final_score": 40,
            "times": "星期二 10:30-12:10"
        }
        cid = client.post("/api/courses", data=json.dumps(to_del),
                          content_type="application/json").get_json()["data"]["id"]

        # 删除
        resp = client.delete(f"/api/courses/{cid}")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        # 再次获取应不再存在
        ids = [c["id"] for c in client.get("/api/courses").get_json()["data"]]
        assert cid not in ids

// auth-api.js
var API_BASE_URL = `http://${window.location.host}/api`;

// 获取当前登录的学生ID
window.getCurrentStudentId = async function () {
    try {
        const userResponse = await fetch(`${API_BASE_URL}/current-user`, {
            credentials: 'include'
        });
        const userData = await handleResponse(userResponse);

        console.log('当前用户信息:', userData);

        if (userData.success && userData.data.student_id) {
            return userData.data.student_id;
        }

        if (userData.success && userData.data.username) {
            const username = userData.data.username;
            const studentsResponse = await getStudents();

            console.log('获取到的学生列表:', studentsResponse);

            if (studentsResponse.success) {
                const student = studentsResponse.data.find(s => s.name === username);
                if (student) {
                    console.log('找到匹配的学生:', student);
                    return student.student_id;
                } else {
                    console.error('未找到匹配的学生记录');
                }
            }
        }
        return null;
    } catch (error) {
        console.error('获取学生ID失败:', error);
        return null;
    }
}

// 获取当前管理员的个人资料
window.getAdminProfile = async function (adminId) {
    try {
        const response = await fetch(`${API_BASE_URL}/admins/${adminId}/profile`, {
            credentials: 'include'
        });
        return handleResponse(response);
    } catch (error) {
        handleError('获取管理员个人资料失败', error);
    }
}

// 更新管理员个人资料
window.updateAdminProfile = async function (adminId, profileData) {
    try {
        const response = await fetch(`${API_BASE_URL}/admins/${adminId}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(profileData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('更新管理员个人资料失败', error);
    }
}

// student-api.js
window.addStudent = async function (studentData) {
    try {
        console.log('发送添加学生请求:', studentData);
        const response = await fetch(`${API_BASE_URL}/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(studentData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('添加学生失败', error);
    }
}

window.updateStudent = async function (studentId, studentData) {
    try {
        console.log('发送更新学生请求:', studentData);
        const response = await fetch(`${API_BASE_URL}/students/${studentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(studentData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('更新学生信息失败', error);
    }
}

window.deleteStudent = async function (studentId) {
    try {
        console.log('发送删除学生请求:', studentId);
        const response = await fetch(`${API_BASE_URL}/students/${studentId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        console.log('删除学生API响应状态:', response.status);

        const result = await handleResponse(response);
        console.log('删除学生API响应数据:', result);

        return result;
    } catch (error) {
        console.error('删除学生失败:', error);
        throw error;
    }
}

window.getStudentCourses = async function (studentId) {
    try {
        console.log('获取学生课程:', studentId);
        const response = await fetch(`${API_BASE_URL}/students/${studentId}/courses`, {
            credentials: 'include'
        });
        return handleResponse(response);
    } catch (error) {
        handleError('获取学生课程失败', error);
    }
}

window.getStudentProfile = async function (studentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/students/${studentId}/profile`, {
            credentials: 'include'
        });
        return handleResponse(response);
    } catch (error) {
        handleError('获取学生个人资料失败', error);
    }
}

window.updateStudentProfile = async function (studentId, profileData) {
    try {
        const response = await fetch(`${API_BASE_URL}/students/${studentId}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(profileData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('更新学生个人资料失败', error);
    }
}

window.getStudents = async function () {
    try {
        console.log('正在获取学生列表...');
        const response = await fetch(`${API_BASE_URL}/students`, {
            credentials: 'include'
        });
        const result = await handleResponse(response);
        console.log('获取到的学生数据:', result.data);
        return result;
    } catch (error) {
        handleError('获取学生列表失败', error);
    }
}

// teacher-api.js
window.addTeacher = async function (teacherData) {
    try {
        console.log('发送添加教师请求:', teacherData);
        const response = await fetch(`${API_BASE_URL}/teachers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(teacherData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('添加教师失败', error);
    }
}

window.updateTeacher = async function (teacherId, teacherData) {
    try {
        console.log('发送更新教师请求:', teacherData);
        const response = await fetch(`${API_BASE_URL}/teachers/${teacherId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(teacherData)
        });
        const result = await handleResponse(response);
        if (result.success) {
            await Promise.all([
                updateTeacherSelectors(),
                updateTeacherLists(),
                updateTeacherCourses()
            ]);
        }
        return result;
    } catch (error) {
        handleError('更新教师信息失败', error);
    }
}

window.deleteTeacher = async function (teacherId) {
    try {
        console.log('发送删除教师请求:', teacherId);
        const response = await fetch(`${API_BASE_URL}/teachers/${teacherId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        return await handleResponse(response);
    } catch (error) {
        console.error('删除教师失败:', error);
        throw error;
    }
}

window.getTeacherProfile = async function (teacherId) {
    try {
        const response = await fetch(`${API_BASE_URL}/teachers/${teacherId}/profile`, {
            credentials: 'include'
        });
        return handleResponse(response);
    } catch (error) {
        handleError('获取教师个人资料失败', error);
    }
}

window.updateTeacherProfile = async function (teacherId, profileData) {
    try {
        const response = await fetch(`${API_BASE_URL}/teachers/${teacherId}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(profileData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('更新教师个人资料失败', error);
    }
}

window.getTeachers = async function () {
    try {
        console.log('正在获取教师列表...');
        const response = await fetch(`${API_BASE_URL}/teachers`, {
            credentials: 'include'
        });
        const result = await handleResponse(response);
        console.log('获取到的教师数据:', result.data);
        return result;
    } catch (error) {
        handleError('获取教师列表失败', error);
    }
}

// course-api.js
window.addCourse = async function (courseData) {
    try {
        console.log('发送添加课程请求:', courseData);
        const response = await fetch(`${API_BASE_URL}/courses`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(courseData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('添加课程失败', error);
    }
}

window.updateCourse = async function (courseId, courseData) {
    try {
        const response = await fetch(`${API_BASE_URL}/courses/${courseId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(courseData)
        });
        return handleResponse(response);
    } catch (error) {
        handleError('更新课程失败', error);
    }
}

window.getCourses = async function () {
    try {
        console.log('正在获取课程列表...');
        const response = await fetch(`${API_BASE_URL}/courses`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('获取到的课程数据:', result);

        if (!result.success) {
            throw new Error(result.message || '获取课程数据失败');
        }

        return result;
    } catch (error) {
        console.error('获取课程列表失败:', error);
        throw error;
    }
}

// grade-api.js
window.getStudentGrades = async function (studentId) {
    try {
        console.log('获取学生成绩:', studentId);
        const response = await fetch(`${API_BASE_URL}/students/${studentId}/grades`, {
            credentials: 'include'
        });
        return handleResponse(response);
    } catch (error) {
        handleError('获取成绩失败', error);
    }
}

window.saveGrades = async function (studentId, grades) {
    try {
        console.log('保存成绩:', { studentId, grades });
        const response = await fetch(`${API_BASE_URL}/grades`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ student_id: studentId, grades: grades })
        });
        return handleResponse(response);
    } catch (error) {
        handleError('保存成绩失败', error);
    }
}

// assignment-api.js
window.addAssignment = async function (courseId, assignmentData) {
    try {
        console.log('发送添加作业请求:', assignmentData);
        const response = await fetch(`${API_BASE_URL}/assignments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(assignmentData)
        });
        const result = await handleResponse(response);
        console.log('添加作业响应:', result);
        return result;
    } catch (error) {
        console.error('添加作业失败:', error);
        throw error;
    }
}

window.getAssignments = async function (courseId) {
    try {
        console.log('获取作业列表:', courseId);
        const response = await fetch(`${API_BASE_URL}/courses/${courseId}/assignments`, {
            credentials: 'include'
        });
        const result = await handleResponse(response);
        console.log('获取作业列表响应:', result);
        return result;
    } catch (error) {
        console.error('获取作业列表失败:', error);
        throw error;
    }
}

window.deleteAssignment = async function (assignmentId) {
    try {
        console.log('发送删除作业请求:', assignmentId);
        const response = await fetch(`${API_BASE_URL}/assignments/${assignmentId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        return await handleResponse(response);
    } catch (error) {
        console.error('删除作业失败:', error);
        throw error;
    }
}

window.updateAssignment = async function (assignmentId, assignmentData) {
    try {
        console.log('发送更新作业请求:', { assignmentId, assignmentData });
        const response = await fetch(`${API_BASE_URL}/assignments/${assignmentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(assignmentData)
        });
        return await handleResponse(response);
    } catch (error) {
        console.error('更新作业失败:', error);
        throw error;
    }
}

// common.js
async function handleResponse(response) {
    try {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const result = await response.json();
            console.log('服务器响应:', result);

            if (!response.ok) {
                throw new Error(result.message || `HTTP error! status: ${response.status}`);
            }

            return result;
        } else {
            const text = await response.text();
            console.error('非JSON响应:', text);
            throw new Error('服务器返回了非JSON格式的响应');
        }
    } catch (error) {
        console.error('响应处理失败:', error);
        throw error;
    }
}

function handleError(message, error) {
    console.error(message + ':', error);
    const errorMessage = error.message || '未知错误';
    alert(message + ': ' + errorMessage);
    throw error;
}

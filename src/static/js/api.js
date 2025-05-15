var API_BASE_URL = `http://${window.location.host}/api`;

// 课程相关API
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

// 学生相关API
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
        return await handleResponse(response);
    } catch (error) {
        console.error('删除学生失败:', error);
        throw error;
    }
}

window.addStudentCourse = async function (studentId, courseId) {
    try {
        console.log('学生选课:', { studentId, courseId });
        const response = await fetch(`${API_BASE_URL}/student-courses`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ student_id: studentId, course_id: courseId })
        });
        return handleResponse(response);
    } catch (error) {
        handleError('选课失败', error);
    }
}

window.dropStudentCourse = async function (studentId, courseId) {
    try {
        console.log('学生退课:', { studentId, courseId });
        const response = await fetch(`${API_BASE_URL}/student-courses`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ student_id: studentId, course_id: courseId })
        });
        return handleResponse(response);
    } catch (error) {
        handleError('退课失败', error);
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

// 获取当前登录的学生ID
window.getCurrentStudentId = async function () {
    try {
        // 获取当前用户信息
        const userResponse = await fetch(`${API_BASE_URL}/current-user`, {
            credentials: 'include'
        });
        const userData = await handleResponse(userResponse);

        console.log('当前用户信息:', userData); // 添加调试信息

        // 如果API直接返回了学生ID，直接使用
        if (userData.success && userData.data.student_id) {
            return userData.data.student_id;
        }

        // 否则，尝试通过用户名查找
        if (userData.success && userData.data.username) {
            const username = userData.data.username;

            // 获取所有学生
            const studentsResponse = await getStudents();

            console.log('获取到的学生列表:', studentsResponse); // 添加调试信息

            if (studentsResponse.success) {
                // 查找用户名匹配的学生
                const student = studentsResponse.data.find(s => s.name === username);
                if (student) {
                    console.log('找到匹配的学生:', student); // 添加调试信息
                    return student.student_id;
                } else {
                    console.error('未找到匹配的学生记录'); // 添加调试信息
                }
            }
        }
        return null;
    } catch (error) {
        console.error('获取学生ID失败:', error);
        return null;
    }
}

// 师相关API
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
            // 更新成功后刷新所有相关数据
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

window.addTeacherCourse = async function (teacherId, courseId) {
    try {
        console.log('安排教师课程:', { teacherId, courseId });
        const response = await fetch(`${API_BASE_URL}/teacher-courses`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ teacher_id: teacherId, course_id: courseId })
        });
        return handleResponse(response);
    } catch (error) {
        handleError('安排课程失败', error);
    }
}

window.getTeacherCourses = async function (teacherId) {
    try {
        console.log('获取教师课程:', teacherId);
        const response = await fetch(`${API_BASE_URL}/teachers/${teacherId}/courses`, {
            credentials: 'include'
        });
        return handleResponse(response);
    } catch (error) {
        handleError('获取教师课程失败', error);
    }
}

// 获取数据的API
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
        handleError('获取教师列表失', error);
    }
}

// 响应处理函数
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
            console.error('非JSON应:', text);
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

// 添加课程选择器更新函数
window.updateCourseSelectors = async function () {
    try {
        const response = await getCourses();
        if (response.success) {
            // 更新所有课程选择器
            const courseSelects = [
                $('#enrollCourseSelect'),
                $('#modifyCourseSelect'),
                $('#deleteCourseSelect')
            ];

            courseSelects.forEach(select => {
                if (select.length) {  // 确保选择器存在
                    select.empty();
                    select.append('<option value="">择课程</option>');
                    response.data.forEach(course => {
                        select.append(`<option value="${course.id}">${course.name}</option>`);
                    });
                }
            });
        }
    } catch (error) {
        console.error('更新课程选择器失败:', error);
    }
}

// 修改刷新数据的函数
window.refreshAllData = async function () {
    try {
        await Promise.all([
            updateTeacherSelectors(),
            updateTeacherLists(),
            updateTeacherCourses(),
            updateCourseSelectors(),
            updateStudentSelectors(),
            updateStudentLists(),
            updateStudentCourses()
        ]);
    } catch (error) {
        console.error('刷新数据失败:', error);
    }
}

// 更新所有教师选择器
window.updateTeacherSelectors = async function () {
    try {
        const response = await getTeachers();
        if (response && response.success) {
            const teacherSelects = [
                $('#teacherSelect'),
                $('#scheduleTeacherSelect'),
                $('#modifyTeacherSelect'),
                $('#deleteTeacherSelect')
            ];

            teacherSelects.forEach(select => {
                if (select.length) {
                    const currentValue = select.val();  // 保存当前选中值
                    select.empty();
                    select.append('<option value="">选择教师</option>');
                    response.data.forEach(teacher => {
                        select.append(`<option value="${teacher.teacher_id}">
                            ${teacher.name} - ${teacher.teacher_id}
                        </option>`);
                    });
                    if (currentValue) {
                        select.val(currentValue);  // 恢复选中值
                    }
                }
            });
        }
    } catch (error) {
        console.error('更新教师选择器失败:', error);
    }
}

// 更教师列表
window.updateTeacherLists = async function () {
    try {
        const response = await getTeachers();
        if (response && response.success) {
            // 更新教师表格（如果存在）
            if ($('#teacherTableBody').length) {
                let html = '';
                response.data.forEach(teacher => {
                    html += `
                        <tr>
                            <td>${teacher.name}</td>
                            <td>${teacher.teacher_id}</td>
                        </tr>
                    `;
                });
                $('#teacherTableBody').html(html);
            }
        }
    } catch (error) {
        console.error('更新教师列表失败:', error);
    }
}

// 更新教师课程信息
window.updateTeacherCourses = async function () {
    try {
        const teacherId = $('#teacherSelect').val();
        if (teacherId) {
            const response = await getTeacherCourses(teacherId);
            if (response && response.success) {
                let html = '';
                if (response.data && response.data.length > 0) {
                    response.data.forEach(course => {
                        html += `
                            <tr>
                                <td>${course.name}</td>
                                <td>${course.learn_time}</td>
                                <td>${course.credit}</td>
                                <td>${course.times || ''}</td>
                            </tr>
                        `;
                    });
                } else {
                    html = '<tr><td colspan="4">暂无课程数据</td></tr>';
                }
                $('#teacherCoursesTableBody').html(html);
            }
        }
    } catch (error) {
        console.error('更新教师课程失败:', error);
    }
}

// 更新所有学生选择器
window.updateStudentSelectors = async function () {
    try {
        const response = await getStudents();
        if (response.success) {
            // 更新所有学生选择器
            const studentSelects = [
                $('#studentSelect'),
                $('#enrollStudentSelect'),
                $('#modifyStudentSelect'),
                $('#deleteStudentSelect')
            ];

            studentSelects.forEach(select => {
                if (select.length) {  // 确保选择器存在
                    select.empty();
                    select.append('<option value="">选择学生</option>');
                    response.data.forEach(student => {
                        select.append(`<option value="${student.student_id}">
                            ${student.name} - ${student.student_id}
                        </option>`);
                    });
                }
            });
        }
    } catch (error) {
        console.error('更新学生选择器失败:', error);
    }
}

// 成绩相关API
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

// 作业相关API
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

// 添加一个通用的过滤函数
function filterDataWithLimit(dataList, searchText, limit = 25) {
    if (!dataList) return [];

    if (!searchText.trim()) {
        // 如果搜索文本为空，返回前25条记录
        return dataList.slice(0, limit);
    }

    // 如果有搜索文本，进行精确匹配
    const searchLower = searchText.toLowerCase();
    return dataList.filter(item => {
        // 根据item的类型判断搜索条件
        if (item.name) {  // 适用于课程、教师、学生
            if (item.student_id) {  // 学生特有
                return item.name.toLowerCase().includes(searchLower) ||
                    item.student_id.toLowerCase().includes(searchLower);
            }
            if (item.teacher_id) {  // 教师特有
                return item.name.toLowerCase().includes(searchLower) ||
                    item.teacher_id.toLowerCase().includes(searchLower);
            }
            // 课程
            return item.name.toLowerCase().includes(searchLower);
        }
        return false;
    });
}

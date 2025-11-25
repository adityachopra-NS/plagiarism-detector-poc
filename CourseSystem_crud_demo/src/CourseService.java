import java.util.ArrayList;
import java.util.List;

public class CourseService {
    private List<Course> courses = new ArrayList<>();
    private int nextId = 1;

    // Create
    public Course createCourse(String name) {
        Course c = new Course(nextId++, name);
        courses.add(c);
        return c;
    }

    // Read
    public List<Course> getAllCourses() {
        return new ArrayList<>(courses);
    }

    public Course getCourseById(int id) {
        for (Course c : courses) {
            if (c.getId() == id) return c;
        }
        return null;
    }

    // Update
    public boolean updateCourse(int id, String newName) {
        Course c = getCourseById(id);
        if (c != null) {
            c.setName(newName);
            return true;
        }
        return false;
    }

    // Delete
    public boolean deleteCourse(int id) {
        Course c = getCourseById(id);
        if (c != null) {
            courses.remove(c);
            return true;
        }
        return false;
    }
}


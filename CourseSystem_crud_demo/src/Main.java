import java.util.List;
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        CourseService cs = new CourseService();
        Scanner sc = new Scanner(System.in);

        cs.createCourse("Mathematics");
        cs.createCourse("Physics");

        System.out.println("Initial courses:");
        printCourses(cs.getAllCourses());

        System.out.println("\nCreating a new course 'Chemistry'...");
        cs.createCourse("Chemistry");
        printCourses(cs.getAllCourses());

        System.out.println("\nUpdating course id=2 to 'Advanced Physics'...");
        cs.updateCourse(2, "Advanced Physics");
        printCourses(cs.getAllCourses());

        System.out.println("\nDeleting course id=1...");
        cs.deleteCourse(1);
        printCourses(cs.getAllCourses());

        sc.close();
    }

    static void printCourses(List<Course> courses) {
        for (Course c : courses) {
            System.out.println(c);
        }
    }
}

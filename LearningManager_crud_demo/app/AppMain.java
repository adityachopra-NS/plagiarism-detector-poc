import java.util.List;

public class AppMain {
    public static void main(String[] args) {
        SubjectService ss = new SubjectService();

        ss.addSubject("Chemistry");
        ss.addSubject("Biology");

        System.out.println("Initial subjects:");
        printAll(ss.listSubjects());

        System.out.println("\nAdding 'Geography' ...");
        ss.addSubject("Geography");
        printAll(ss.listSubjects());

        System.out.println("\nEditing id=2 to 'Advanced Biology'...");
        ss.editSubject(2, "Advanced Biology");
        printAll(ss.listSubjects());

        System.out.println("\nRemoving id=1 ...");
        ss.removeSubject(1);
        printAll(ss.listSubjects());
    }

    static void printAll(List<Subject> list) {
        for (Subject s : list) {
            System.out.println(s);
        }
    }
}

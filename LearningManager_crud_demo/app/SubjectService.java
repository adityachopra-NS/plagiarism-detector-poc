package LearningManager_crud_demo.app;

public class SubjectService {
    
}
import java.util.ArrayList;
import java.util.List;

public class SubjectService {
    private List<Subject> list = new ArrayList<>();
    private int counter = 1;

    public Subject addSubject(String title) {
        Subject s = new Subject(counter++, title);
        list.add(s);
        return s;
    }

    public List<Subject> listSubjects() {
        return new ArrayList<>(list);
    }

    public Subject findById(int id) {
        for (Subject s : list) {
            if (s.getId() == id) return s;
        }
        return null;
    }

    public boolean editSubject(int id, String newTitle) {
        Subject s = findById(id);
        if (s != null) {
            s.setTitle(newTitle);
            return true;
        }
        return false;
    }

    public boolean removeSubject(int id) {
        Subject s = findById(id);
        if (s != null) {
            list.remove(s);
            return true;
        }
        return false;
    }
}

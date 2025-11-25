public class Subject {
    private int id;
    private String title;

    public Subject(int id, String title) {
        this.id = id;
        this.title = title;
    }

    public int getId() { return id; }
    public String getTitle() { return title; }
    public void setTitle(String t) { this.title = t; }

    @Override
    public String toString() {
        return "Subject{id=" + id + ", title='" + title + "'}";
    }
}

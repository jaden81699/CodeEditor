import java.lang.reflect.Method;

public class CountPositiveRunner {
    public static void main(String[] args) {
        try {
            Class<?> mainClass = Class.forName("Main");
            Object mainInstance = mainClass.getDeclaredConstructor().newInstance();
            Method countPositiveMethod = mainClass.getMethod("countPositive", int[].class);
            int[] numbers = {3, 5, 12, -4, -1, 5, 4, -7, 9, 0};
            int actual = (Integer) countPositiveMethod.invoke(mainInstance, (Object) numbers);
            int expected = 6;
            System.out.println("Actual: " + actual);
            System.out.println("Expected: " + expected);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
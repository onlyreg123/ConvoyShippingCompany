def range_sum(numbers, start, end):
    return sum([i if start <= i <= end else 0 for i in numbers])


input_numbers =  [int(i) for i in input().split()]
a, b = [int(i) for i in input().split()]
print(range_sum(input_numbers, a, b))

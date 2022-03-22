import constants
import pandas as pd
from pandas_profiling import ProfileReport


def main():
    df = pd.read_csv('evaluation_minimal_fields.csv')
    prof = ProfileReport(df)
    prof.to_file(output_file='evaluation_report.html')


if __name__ == '__main__':
    main()

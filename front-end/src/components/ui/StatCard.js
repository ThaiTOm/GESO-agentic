import styles from './StatCard.module.css';

const StatCard = ({ icon, title, value, change }) => {
    const isPositive = change.startsWith('+');
    return (
        <div className={styles.statCard}>
            <div className={styles.iconWrapper}>{icon}</div>
            <div className={styles.info}>
                <p className={styles.title}>{title}</p>
                <p className={styles.value}>{value}</p>
                <p className={`${styles.change} ${isPositive ? styles.positive : styles.negative}`}>
                    {change}
                </p>
            </div>
        </div>
    );
};
export default StatCard;